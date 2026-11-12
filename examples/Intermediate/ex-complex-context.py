import random
from maspy import *

class ContextAgent(Agent):
    @pl(gain, Goal("evaluate"),
        (Belief("temp", Any) < 25) & ~Belief("override")
    )
    def cool_state_plan(self, src, temp):
        self.print(f"[Cool State Plan] Triggered! Temp ({temp}) is below 25 and no override is active.")

    @pl(gain, Goal("evaluate"),
        (Belief("temp", Any) > 35) | (Belief("pressure", Any) >= 12)
    )
    def high_stress_plan(self, src, temp, pressure):
        self.print(f"[High Stress Plan] Triggered! Temp: {temp}, Pressure: {pressure}")

    @pl(gain, Goal("evaluate"),
        (Belief("temp", Any) <= 35) & (Belief("temp", Any) >= 25) & (Belief("status", Any) != "error")
    )
    def nominal_state_plan(self, src, temp, status):
        self.print(f"[Nominal Plan] Triggered! Temp: {temp} (nominal range), Status: {status}")

    @pl(gain, Goal("evaluate"),
        Belief("mode", "auto") ^ Belief("safe_mode")
    )
    def exclusive_mode_plan(self, src):
        self.print(f"[Exclusive Mode Plan] Triggered! XOR condition met between auto mode and safe mode.")

    @pl(gain, Goal("evaluate"))
    def default_plan(self, src):
        self.print(f"No Plan was Applicable with The Randomized Context.")
            
    def on_idle(self):
        self.stop_cycle()
            
if __name__ == '__main__': 
    # Randomly seed environment values to ensure non-deterministic plan execution across runs
    # Run this code multiple times to check which plans are executed each time by the same Goal in different contexts
    t = random.randint(15, 40)
    p = random.randint(5, 15)
    override_val = random.choice([True, False])
    status_val = random.choice(["ok", "warning", "error"])
    auto_mode = random.choice([True, False])
    safe_mode = random.choice([True, False])

    print("   Random Context:")
    print(f"\tTemperature - {t}")
    print(f"\tPressure    - {p}")
    print(f"\tOverride    - {override_val}")
    print(f"\tStatus      - {status_val}")
    print(f"\tAuto Mode   - {auto_mode}")
    print(f"\tSafe Mode   - {safe_mode}\n")
    print("   Context Agent Plans Requirements:")
    print("\t[Cool State Plan]: Temperature Less Than 25 and No Override Active")
    print("\t[High Stress Plan]: Temperature Greater Than 35 or Pressure Greater Than or Equal To 12")
    print("\t[Nominal Plan]: Temperature Between 25 and 35 and Status Not Error")
    print("\t[Exclusive Mode Plan]: Either Auto Mode or Safe Mode On, not both nor neither")

    ag = ContextAgent("Controller", 
                      beliefs=[
                        Belief("temp", t),
                        Belief("pressure", p),
                        Belief("status", status_val),
                        Belief("mode", "auto" if auto_mode else "manual"),
                        Belief("override") if override_val else Belief("safe_mode")
                        ],
                      goals=[
                        Goal("evaluate")
                        ]
                    )
    
    Admin().start_system()