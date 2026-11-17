// DeltaFiltre — baseline-relative alarm state machine (docs/06-method.md §4).
//
//   E(t) = dP_norm(t) - B_n
//   Alarm ON : E >= delta for `persistence` consecutive VALID windows
//   Alarm OFF: E <  delta - hysteresis
// Invalid windows (no flow, transient, sensor fault) never advance the
// persistence counter and never clear an active alarm.
#pragma once
#include <cstdint>

namespace df {

enum class AlarmState : uint8_t { OK, PENDING, ALARM };

struct AlarmConfig {
  float delta_kpa = 20.0f;       // adjustable 20-40 kPa (spec EF-11)
  float hysteresis_kpa = 5.0f;   // h
  uint8_t persistence = 3;       // consecutive valid windows required
};

class AlarmFsm {
 public:
  explicit AlarmFsm(AlarmConfig cfg) : cfg_(cfg) {}

  // Feed one 5-minute window. `valid` = window may be compared to baseline.
  // Returns the state after this window.
  AlarmState update(float excess_kpa, bool valid) {
    if (!valid) return state_;  // frozen: no advance, no clear
    if (state_ == AlarmState::ALARM) {
      if (excess_kpa < cfg_.delta_kpa - cfg_.hysteresis_kpa) {
        state_ = AlarmState::OK;
        pending_ = 0;
      }
      return state_;
    }
    if (excess_kpa >= cfg_.delta_kpa) {
      if (++pending_ >= cfg_.persistence) {
        state_ = AlarmState::ALARM;
        pending_ = 0;
      } else {
        state_ = AlarmState::PENDING;
      }
    } else {
      pending_ = 0;
      state_ = AlarmState::OK;
    }
    return state_;
  }

  AlarmState state() const { return state_; }
  uint8_t pending() const { return pending_; }
  void reset() { state_ = AlarmState::OK; pending_ = 0; }

 private:
  AlarmConfig cfg_;
  AlarmState state_ = AlarmState::OK;
  uint8_t pending_ = 0;
};

}  // namespace df
