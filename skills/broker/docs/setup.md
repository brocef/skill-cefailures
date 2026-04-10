# Broker Setup

## 1. Install the CLI

Create a symlink so `broker` is available in your `$PATH`:

```bash
ln -s /path/to/skill-cefailures/scripts/broker_cli.py /usr/local/bin/broker
```

Or add the scripts directory to your PATH:

```bash
export PATH="/path/to/skill-cefailures/scripts:$PATH"
```

If using the symlink approach, make sure the script is executable:

```bash
chmod +x /path/to/skill-cefailures/scripts/broker_cli.py
```

## 2. Start the broker server

The broker server must be running before agents can connect:

```bash
broker server
broker server --identity brian    # custom identity (default: "user")
```

This starts the Unix domain socket server at `~/.mcp-broker/broker.sock` and opens an interactive REPL. Conversations are persisted to `~/.mcp-broker/conversations/`.

To join from a separate terminal without running the server:

```bash
broker repl --identity observer
```

## 3. Configure Claude Code permissions

Add `Bash(broker:*)` to your allowedTools so agents can call the broker without permission prompts:

In your Claude Code settings or project CLAUDE.md:

```
allowedTools:
  - Bash(broker:*)
```

## 4. Install the skill

### As a plugin (recommended)

```
/plugin marketplace add brocef/skill-cefailures
/plugin install skill-cefailures
```

### Local development

```bash
claude --plugin-dir /path/to/skill-cefailures
```

## 5. Tell agents to use the broker

Once the server is running and the skill is installed, tell agents:

```
You have a broker CLI. Check for conversations with `broker list --identity <your-name>` and respond to any messages.
```

Agents will use the skill's polling pattern to keep checking for new messages.
