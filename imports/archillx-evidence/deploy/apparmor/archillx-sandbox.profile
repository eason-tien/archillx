#include <tunables/global>
profile archillx-sandbox flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  deny network,
  file,
  /usr/bin/python3 ixr,
  /sandbox/** rw,
  /tmp/** rw,
  deny /proc/** w,
  deny /sys/** w,
}
