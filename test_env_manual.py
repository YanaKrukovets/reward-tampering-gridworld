from env import TamperGridEnv

env = TamperGridEnv(mode="blatant_cheater")
obs, info = env.reset()
env.render()

# walk toward the tamper cell at (3,3): down x3, then right x3
for action in [1, 1, 1, 3, 3, 3]:
    obs, reward, terminated, truncated, info = env.step(action)
    env.render()
    print(f"reward={reward:.2f}  true_done={info['true_done']}  sensor_triggered={info['sensor_triggered']}")
