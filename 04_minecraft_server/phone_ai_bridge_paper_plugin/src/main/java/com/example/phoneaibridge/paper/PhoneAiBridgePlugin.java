package com.example.phoneaibridge.paper;

import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

public final class PhoneAiBridgePlugin extends JavaPlugin implements CommandExecutor, TabCompleter, Listener {
    private static final PlainTextComponentSerializer PLAIN_TEXT = PlainTextComponentSerializer.plainText();

    private final Map<UUID, Long> cooldownUntilMillis = new ConcurrentHashMap<>();
    private DashboardEventClient client;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        reloadClient();
        registerCommand("ai");
        registerCommand("phoneai");
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("PhoneAiBridge enabled. Dashboard URL: " + client.baseUrl());
    }

    @Override
    public void onDisable() {
        cooldownUntilMillis.clear();
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (command.getName().equalsIgnoreCase("phoneai")) {
            return handleAdminCommand(sender, args);
        }

        if (args.length == 0) {
            sender.sendMessage(prefix() + " Usage: /ai <question>");
            return true;
        }

        Player player = sender instanceof Player p ? p : null;
        ask(sender, player, String.join(" ", args));
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!command.getName().equalsIgnoreCase("phoneai") || args.length != 1) {
            return Collections.emptyList();
        }

        String prefix = args[0].toLowerCase(Locale.US);
        return Arrays.asList("status", "health", "reload").stream()
                .filter(value -> value.startsWith(prefix))
                .toList();
    }

    @EventHandler
    public void onAsyncChat(AsyncChatEvent event) {
        if (!getConfig().getBoolean("chat_trigger.enabled", true)) {
            return;
        }

        String trigger = matchingTrigger(PLAIN_TEXT.serialize(event.message()).trim());
        if (trigger == null) {
            return;
        }

        String message = PLAIN_TEXT.serialize(event.message()).trim();
        event.setCancelled(true);
        String question = message.length() == trigger.length() ? "" : message.substring(trigger.length()).trim();
        Bukkit.getScheduler().runTask(this, () -> ask(event.getPlayer(), event.getPlayer(), question));
    }

    private boolean handleAdminCommand(CommandSender sender, String[] args) {
        String action = args.length == 0 ? "status" : args[0].toLowerCase(Locale.US);
        switch (action) {
            case "status" -> {
                sender.sendMessage(prefix() + " Dashboard URL: " + client.baseUrl());
                sender.sendMessage(prefix() + " Chat triggers: " + triggers());
                return true;
            }
            case "reload" -> {
                reloadConfig();
                reloadClient();
                sender.sendMessage(prefix() + " Config reloaded. Dashboard URL: " + client.baseUrl());
                return true;
            }
            case "health" -> {
                sender.sendMessage(prefix() + " Checking dashboard event bridge...");
                Bukkit.getScheduler().runTaskAsynchronously(this, () -> {
                    try {
                        String response = client.status();
                        runSync(() -> sender.sendMessage(prefix() + " Dashboard event status: " + compact(response)));
                    } catch (Exception e) {
                        getLogger().log(Level.WARNING, "Dashboard event bridge health check failed", e);
                        runSync(() -> sender.sendMessage(prefix() + " Health check failed: " + e.getMessage()));
                    }
                });
                return true;
            }
            default -> {
                sender.sendMessage(prefix() + " Usage: /phoneai <status|health|reload>");
                return true;
            }
        }
    }

    private void ask(CommandSender sender, Player player, String question) {
        if (question == null || question.isBlank()) {
            sender.sendMessage(prefix() + " Usage: /ai <question> or !ai <question>");
            return;
        }

        if (player != null && !player.hasPermission("phoneaibridge.ask")) {
            sender.sendMessage(prefix() + " You do not have permission to ask the AI.");
            return;
        }

        if (player != null && isCoolingDown(player)) {
            sender.sendMessage(prefix() + " Please wait a few seconds before asking again.");
            return;
        }

        sender.sendMessage(prefix() + " Queuing question for phone AI...");
        DashboardEvent request = new DashboardEvent(
                player == null ? "" : player.getUniqueId().toString(),
                player == null ? sender.getName() : player.getName(),
                "!ai " + question.trim(),
                serverContext(),
                coordinateContext(player),
                Math.max(1, getConfig().getInt("phone_ai.max_tokens", 180))
        );

        Bukkit.getScheduler().runTaskAsynchronously(this, () -> {
            try {
                client.submit(request);
                runSync(() -> sender.sendMessage(prefix() + " Queued. The answer will come back through server chat."));
            } catch (Exception e) {
                getLogger().log(Level.WARNING, "Dashboard event submit failed", e);
                runSync(() -> sender.sendMessage(prefix() + " Event submit failed: " + e.getMessage()));
            }
        });
    }

    private boolean isCoolingDown(Player player) {
        long now = System.currentTimeMillis();
        long until = cooldownUntilMillis.getOrDefault(player.getUniqueId(), 0L);
        if (until > now) {
            return true;
        }

        int cooldownSeconds = Math.max(0, getConfig().getInt("limits.cooldown_seconds", 5));
        if (cooldownSeconds > 0) {
            cooldownUntilMillis.put(player.getUniqueId(), now + cooldownSeconds * 1000L);
        }
        return false;
    }

    private String serverContext() {
        String tps = Arrays.stream(Bukkit.getTPS())
                .mapToObj(value -> String.format(Locale.US, "%.2f", value))
                .reduce((left, right) -> left + "," + right)
                .orElse("unknown");
        return "online_players=" + Bukkit.getOnlinePlayers().size()
                + "/" + Bukkit.getMaxPlayers()
                + "; tps_1m_5m_15m=" + tps;
    }

    private String coordinateContext(Player player) {
        if (player == null) {
            return "";
        }

        Location location = player.getLocation();
        World world = location.getWorld();
        String worldName = world == null ? "unknown" : world.getName();
        return String.format(
                Locale.US,
                "player_location world=%s x=%.1f y=%.1f z=%.1f yaw=%.1f pitch=%.1f gamemode=%s",
                worldName,
                location.getX(),
                location.getY(),
                location.getZ(),
                location.getYaw(),
                location.getPitch(),
                player.getGameMode().name().toLowerCase(Locale.US)
        );
    }

    private void reloadClient() {
        client = DashboardEventClient.fromConfig(getConfig());
    }

    private List<String> triggers() {
        List<String> configured = getConfig().getStringList("chat_trigger.prefixes");
        if (!configured.isEmpty()) {
            return configured;
        }

        String legacy = getConfig().getString("chat_trigger.prefix", "!ai");
        return legacy == null || legacy.isBlank() ? List.of("!ai") : List.of(legacy);
    }

    private String matchingTrigger(String message) {
        for (String trigger : triggers()) {
            if (trigger == null || trigger.isBlank()) {
                continue;
            }
            if (message.equals(trigger) || message.startsWith(trigger + " ")) {
                return trigger;
            }
        }
        return null;
    }

    private String compact(String value) {
        String compacted = value == null ? "" : value.replaceAll("\\s+", " ").trim();
        return compacted.length() > 220 ? compacted.substring(0, 220) + "..." : compacted;
    }

    private void registerCommand(String name) {
        PluginCommand command = getCommand(name);
        if (command == null) {
            getLogger().warning("Command not found in plugin.yml: " + name);
            return;
        }
        command.setExecutor(this);
        command.setTabCompleter(this);
    }

    private void runSync(Runnable runnable) {
        Bukkit.getScheduler().runTask(this, runnable);
    }

    private String prefix() {
        return getConfig().getString("responses.prefix", "[AI]");
    }
}
