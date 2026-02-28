# Evolution Navigation

The evolution navigation page is the subsystem landing page for operators, reviewers, and approvers.

## Primary endpoints

- `GET /v1/evolution/nav`
- `POST /v1/evolution/nav/render`
- `GET /v1/evolution/summary`
- `GET /v1/evolution/evidence/index`
- `GET /v1/evolution/proposals/list`
- `GET /v1/evolution/actions/list`

## What the navigation page includes

- primary routes
- linked docs
- pipeline snapshot
- proposal status overview
- latest workflow objects
- bundle paths
- evidence navigation shortcuts

## Output bundle

`POST /v1/evolution/nav/render` writes:

- JSON
- Markdown
- HTML

under `evidence/evolution/dashboards/`.


- `docs/EVOLUTION_PORTAL.md`
