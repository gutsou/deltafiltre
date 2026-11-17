// DeltaFiltre — quality flags for logged records (see docs/04-data-format.md).
// Hardware-independent core: no Arduino includes in this folder.
#pragma once
#include <cstdint>

namespace df {

// Bitfield stored per logged aggregate.
enum QualityFlag : uint16_t {
  FLAG_NONE            = 0,
  FLAG_ZERO_UNVERIFIED = 1u << 0,  // no recent valid zero check
  FLAG_SENSOR_DRIFT    = 1u << 1,  // last zero check exceeded tolerance
  FLAG_TIME_JUMP       = 1u << 2,  // RTC jump detected
  FLAG_SD_FAULT        = 1u << 3,  // SD write failed for this record
  FLAG_SENSOR_OOR      = 1u << 4,  // reading outside plausible 4-96% of span
  FLAG_NO_FLOW         = 1u << 5,  // pump off / no flow: window invalid for alarm
  FLAG_TRANSIENT       = 1u << 6,  // hydraulic transient: window invalid for alarm
  FLAG_LOW_BATT        = 1u << 7,  // battery below alert threshold
};

}  // namespace df
