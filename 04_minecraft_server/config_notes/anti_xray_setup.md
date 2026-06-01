# Paper Anti-Xray Setup

Paper Anti-Xray is configured in world config files and requires a full server restart.

Prepared examples:

- `paper-world-defaults.anti-xray.yml` goes into `04_minecraft_server/config/paper-world-defaults.yml`.
- `world_nether-paper-world.anti-xray.yml` goes into `04_minecraft_server/world_nether/paper-world.yml`.

The examples use `engine-mode: 1` for low overhead on Raspberry Pi. This hides fully covered ores and ancient debris from normal X-ray clients, but it does not hide ore exposed to caves or water.
