#!/bin/sh

# Mi Box 4 runtime hardware smoke test for LibreELEC.
# Copy to /storage and run over SSH.  Default mode is read-only.
set -u

STATE=/storage/.mibox4-hw-test.state
EXPECT_GPIOAO4=0x00100000
PASS=0
FAIL=0
WARN=0

ok()   { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$*"; }
warn() { WARN=$((WARN + 1)); printf 'WARN: %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

check_gpio_power()
{
  have devmem || { warn 'devmem is unavailable; skipped GPIO register check'; return; }
  value=$(devmem 0xc8100024 32 2>/dev/null || echo unavailable)
  case "$value" in
    0x*|0X*)
      # GPIOAO_4 must be output (bit 4 cleared in EN_N) and high (bit 20 set).
      numeric=$((value))
      expected=$((EXPECT_GPIOAO4))
      if [ $((numeric & 0x00100010)) -eq "$expected" ]; then
        ok "GPIOAO_4 output-high (AO register $value)"
      else
        fail "GPIOAO_4 is not output-high (AO register $value; expected bit mask 0x00100010)"
      fi
      ;;
    *) fail "cannot read AO GPIO register: $value" ;;
  esac
}

check_usb()
{
  have lsusb || { warn 'lsusb is unavailable; skipped USB enumeration check'; return; }
  usb=$(lsusb 2>/dev/null || true)
  printf '%s\n' "$usb" | grep -q '1d6b:0002' && ok 'USB root hub enumerated' || fail 'USB root hub missing'
  printf '%s\n' "$usb" | grep -Eiq 'Genesys|05e3:0610' && ok 'external USB hub enumerated' || fail 'external USB hub missing (check 5V power)'
  printf '%s\n' "$usb" | grep -Eiq '046d:c077|046d:c31d' && ok 'USB HID device enumerated' || warn 'no Logitech HID device found'
}

check_hdmi()
{
  found=0
  for status in /sys/class/drm/*/status; do
    [ -f "$status" ] || continue
    found=1
    state=$(cat "$status" 2>/dev/null || true)
    case "$state" in
      connected) ok "HDMI connector connected ($(basename "$(dirname "$status")"))"; return ;;
      disconnected) warn "HDMI connector reports disconnected ($(basename "$(dirname "$status")"))"; return ;;
    esac
  done
  [ "$found" -eq 1 ] || warn 'DRM status is unavailable; HDMI power was checked through GPIO'
}

check_wifi()
{
  have iw || { warn 'iw is unavailable; skipped Wi-Fi check'; return; }
  # `iw dev` indents interface lines below each phy (usually with a tab).
  iface=$(iw dev 2>/dev/null | sed -n 's/^[[:space:]]*Interface[[:space:]]\+//p' | head -n 1)
  if [ -n "$iface" ]; then
    ok "Wi-Fi interface present ($iface)"
  else
    fail 'Wi-Fi interface missing'
  fi
}

check_storage()
{
  grep -q ' /storage ' /proc/mounts 2>/dev/null && ok '/storage is mounted' || fail '/storage is not mounted'
  ls /dev/mmcblk* >/dev/null 2>&1 && ok 'eMMC block device present' || fail 'eMMC block device missing'
}

check_reboot_result()
{
  [ -f "$STATE" ] || return
  old_id=$(sed -n 's/^boot_id=//p' "$STATE" | head -n 1)
  new_id=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)
  if [ -n "$old_id" ] && [ "$old_id" != "$new_id" ]; then
    ok "warm reboot completed (boot ID changed)"
    rm -f "$STATE"
  else
    warn 'reboot was requested but boot ID did not change'
  fi
}

request_reboot()
{
  boot_id=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)
  {
    echo "boot_id=$boot_id"
    echo "requested_at=$(date -Ins)"
  } > "$STATE"
  sync
  printf 'Reboot marker saved to %s\n' "$STATE"
  systemctl reboot
}

printf 'Mi Box 4 hardware test — %s\n' "$(date -Ins)"
printf 'Kernel: '; uname -r 2>/dev/null || echo unknown
check_reboot_result
check_gpio_power
check_usb
check_hdmi
check_wifi
check_storage

if [ "${1:-}" = '--reboot' ]; then
  request_reboot
  exit 0
fi

printf '\nSummary: PASS=%s WARN=%s FAIL=%s\n' "$PASS" "$WARN" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
printf 'To test warm reboot, run: %s --reboot\n' "$0"
exit 0
