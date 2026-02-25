"""
ArcHillx v1.0.0 — Multi-Provider Model Router
支援 Anthropic / OpenAI / Google / Groq / Mistral / OLLAMA / Custom endpoint。

Provider 格式：  "provider:model_id"
  anthropic:claude-sonnet-4-6
  openai:gpt-4o
  google:gemini-2.0-flash
  groq:llama-3.3-70b-versatile
  mistral:mistral-large-latest
  ollama:llama3.2
  custom:my-model
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger("archillx.model_router")


def _settings():
    from ..config import settings
    return settings


@dataclass
class ModelResponse:
    model: str
    provider: str
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    stop_reason: str


class BaseProvider:
    name: str = "base"

    def complete(self, model: str, messages: list[dict],
                 system: str | None, max_tokens: int) -> ModelResponse:
        raise NotImplementedError


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        import anthropic as _a
        self._client = _a.Anthropic(api_key=api_key)

    def complete(self, model, messages, system, max_tokens):
        kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens,
                                   "messages": messages}
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)
        content = "".join(b.text for b in resp.content if hasattr(b, "text"))
        return ModelResponse(model=model, provider=self.name, content=content,
                             input_tokens=resp.usage.input_tokens,
                             output_tokens=resp.usage.output_tokens,
                             total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
                             stop_reason=resp.stop_reason or "end_turn")


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, name: str, api_key: str, base_url: str | None = None):
        from openai import OpenAI
        self.name = name
        self._client = OpenAI(api_key=api_key or "not-needed", base_url=base_url)

    def complete(self, model, messages, system, max_tokens):
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        resp = self._client.chat.completions.create(model=model, messages=msgs,
                                                     max_tokens=max_tokens)
        c = resp.choices[0]
        u = resp.usage
        return ModelResponse(model=model, provider=self.name,
                             content=c.message.content or "",
                             input_tokens=u.prompt_tokens if u else 0,
                             output_tokens=u.completion_tokens if u else 0,
                             total_tokens=(u.prompt_tokens + u.completion_tokens) if u else 0,
                             stop_reason=c.finish_reason or "stop")


class GoogleProvider(BaseProvider):
    name = "google"

    def __init__(self, api_key: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai

    def complete(self, model, messages, system, max_tokens):
        history, last_user = [], ""
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            text = m["content"] if isinstance(m["content"], str) else str(m["content"])
            if role == "user":
                last_user = text
                if len(messages) > 1:
                    history.append({"role": "user", "parts": [text]})
            else:
                history.append({"role": "model", "parts": [text]})
        if history and history[-1]["role"] == "user":
            last_user = history.pop()["parts"][0]
        gm = self._genai.GenerativeModel(model_name=model, system_instruction=system or "")
        resp = gm.start_chat(history=history).send_message(last_user) if history \
            else gm.generate_content(last_user)
        try:
            in_tok = resp.usage_metadata.prompt_token_count
            out_tok = resp.usage_metadata.candidates_token_count
        except Exception:
            in_tok = out_tok = 0
        return ModelResponse(model=model, provider=self.name, content=resp.text or "",
                             input_tokens=in_tok, output_tokens=out_tok,
                             total_tokens=in_tok + out_tok, stop_reason="stop")


@dataclass
class RoutingRules:
    default: str = "anthropic:claude-sonnet-4-6"
    task_type_rules: list[dict] = field(default_factory=list)
    budget_rules: list[dict] = field(default_factory=list)
    fallback_chain: list[str] = field(default_factory=list)
    providers: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path) -> "RoutingRules":
        try:
            with open(path) as f:
                d = yaml.safe_load(f)
            return cls(default=d.get("default", "anthropic:claude-sonnet-4-6"),
                       task_type_rules=d.get("task_type_rules", []),
                       budget_rules=d.get("budget_rules", []),
                       fallback_chain=d.get("fallback_chain", []),
                       providers=d.get("providers", {}))
        except Exception as e:
            logger.warning("routing_rules load failed: %s — using defaults", e)
            return cls()


class ModelRouter:
    _MAX: dict[str, int] = {
        "anthropic:claude-opus-4-6": 8192,
        "anthropic:claude-sonnet-4-6": 4096,
        "anthropic:claude-haiku-4-5-20251001": 2048,
        "openai:gpt-4o": 4096, "openai:gpt-4o-mini": 4096, "openai:o1": 8192,
        "google:gemini-2.0-flash": 4096, "google:gemini-1.5-pro": 8192,
        "groq:llama-3.3-70b-versatile": 4096, "groq:llama-3.1-8b-instant": 2048,
        "mistral:mistral-large-latest": 4096, "mistral:mistral-small-latest": 2048,
    }

    def __init__(self):
        s = _settings()
        self._rules = RoutingRules.load(s.routing_rules_path)
        self._providers: dict[str, BaseProvider] = {}
        self._init_providers(s)

    def _init_providers(self, s) -> None:
        def _try(name, factory):
            try:
                self._providers[name] = factory()
                logger.info("Provider ready: %s", name)
            except Exception as e:
                logger.warning("Provider %s init failed: %s", name, e)

        if s.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"):
            key = s.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
            _try("anthropic", lambda: AnthropicProvider(key))

        if s.openai_api_key or os.getenv("OPENAI_API_KEY"):
            key = s.openai_api_key or os.getenv("OPENAI_API_KEY", "")
            _try("openai", lambda: OpenAICompatibleProvider("openai", key, s.openai_base_url))

        if s.google_api_key or os.getenv("GOOGLE_API_KEY"):
            key = s.google_api_key or os.getenv("GOOGLE_API_KEY", "")
            _try("google", lambda: GoogleProvider(key))

        if s.groq_api_key or os.getenv("GROQ_API_KEY"):
            key = s.groq_api_key or os.getenv("GROQ_API_KEY", "")
            _try("groq", lambda: OpenAICompatibleProvider("groq", key,
                                                           "https://api.groq.com/openai/v1"))

        if s.mistral_api_key or os.getenv("MISTRAL_API_KEY"):
            key = s.mistral_api_key or os.getenv("MISTRAL_API_KEY", "")
            _try("mistral", lambda: OpenAICompatibleProvider("mistral", key,
                                                              "https://api.mistral.ai/v1"))

        if s.ollama_enabled or os.getenv("OLLAMA_ENABLED", "").lower() == "true":
            _try("ollama", lambda: OpenAICompatibleProvider("ollama", "ollama",
                                                             s.ollama_base_url))

        if s.custom_model_base_url or os.getenv("CUSTOM_MODEL_BASE_URL"):
            url = s.custom_model_base_url or os.getenv("CUSTOM_MODEL_BASE_URL", "")
            key = s.custom_model_api_key or os.getenv("CUSTOM_MODEL_API_KEY", "not-needed")
            _try("custom", lambda: OpenAICompatibleProvider("custom", key, url))

        for pname, pconf in self._rules.providers.items():
            if pname not in self._providers:
                _try(pname, lambda: OpenAICompatibleProvider(
                    pname, pconf.get("api_key", ""), pconf.get("base_url")))

        if not self._providers:
            logger.warning("No AI providers initialized. Set at least one API key in .env")

    def _parse(self, m: str) -> tuple[str, str]:
        if ":" in m:
            p, mid = m.split(":", 1)
            return p.lower(), mid
        ml = m.lower()
        if ml.startswith("claude"):       return "anthropic", m
        if ml.startswith(("gpt", "o1", "o3")): return "openai", m
        if ml.startswith("gemini"):       return "google", m
        if ml.startswith(("llama", "mixtral", "gemma")):
            return ("ollama" if "ollama" in self._providers else "groq"), m
        if ml.startswith(("mistral", "codestral")): return "mistral", m
        p, _ = self._parse(self._rules.default)
        return p, m

    def select_model(self, task_type: str = "general",
                     budget: str = "medium") -> tuple[str, int]:
        for rule in self._rules.task_type_rules:
            if task_type in rule.get("match", []):
                m = rule["model"]
                p, _ = self._parse(m)
                if p in self._providers:
                    return m, rule.get("max_tokens", self._MAX.get(m, 4096))
        for rule in self._rules.budget_rules:
            if rule.get("budget") == budget:
                m = rule["model"]
                p, _ = self._parse(m)
                if p in self._providers:
                    return m, self._MAX.get(m, 4096)
        m = self._rules.default
        p, _ = self._parse(m)
        if p in self._providers:
            return m, self._MAX.get(m, 4096)
        if self._providers:
            pn = next(iter(self._providers))
            s = _settings()
            fb = {"anthropic": "anthropic:claude-sonnet-4-6",
                  "openai": "openai:gpt-4o-mini",
                  "google": "google:gemini-2.0-flash",
                  "groq": "groq:llama-3.3-70b-versatile",
                  "mistral": "mistral:mistral-small-latest",
                  "ollama": f"ollama:{s.ollama_default_model}"}.get(pn, f"{pn}:default")
            return fb, 4096
        raise RuntimeError("No AI providers available. Set at least one API key.")

    def complete(self, prompt: str, system: str | None = None,
                 task_type: str = "general", budget: str = "medium",
                 messages: list[dict] | None = None,
                 model: str | None = None,
                 max_tokens: int | None = None) -> ModelResponse:
        chosen = model or self.select_model(task_type, budget)[0]
        final_max = max_tokens or self._MAX.get(chosen, 4096)
        msgs = messages or [{"role": "user", "content": prompt}]
        chain = [chosen] + [m for m in self._rules.fallback_chain if m != chosen]
        last_err = None
        for m_str in chain:
            pn, mid = self._parse(m_str)
            p = self._providers.get(pn)
            if not p:
                continue
            try:
                logger.info("Calling %s/%s  task=%s", pn, mid, task_type)
                return p.complete(mid, msgs, system, final_max)
            except Exception as e:
                logger.warning("%s/%s failed: %s", pn, mid, e)
                last_err = e
        raise RuntimeError(f"All providers failed. Last: {last_err}")

    def list_providers(self) -> list[dict]:
        return [{"provider": n, "type": type(p).__name__}
                for n, p in self._providers.items()]

    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    def is_available(self, provider: str) -> bool:
        return provider in self._providers


_instance: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _instance
    if _instance is None:
        _instance = ModelRouter()
    return _instance


class _Proxy:
    def __getattr__(self, name):
        return getattr(get_router(), name)


model_router: ModelRouter = _Proxy()  # type: ignore
