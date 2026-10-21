# OpenAI legacy user API key migration

OpenAI scheduled legacy user API keys for deactivation on **October 22, 2026**. Migrate when OpenAI has notified the organization that a key is affected or the key appears in the legacy **User API Keys** list.

A key already created inside the intended OpenAI project does not need replacement solely because of this deadline.

## What changed

The key's ownership and scope changed:

- a legacy user key was tied to a user at the organization level;
- a replacement key is created inside one project and uses that project's access, permissions, limits, and accounting;
- unattended deployments may use either a user-owned project key or a project service-account key.

The HTTP authentication format did not change. Continue using `OPENAI_API_KEY` and `Authorization: Bearer <key>`. A project key already identifies its project. `OPENAI_ORG_ID` and `OPENAI_PROJECT_ID` remain optional explicit routing overrides, not requirements for a normal project key.

ChatKeke v0.8.5 removes the mutable process-global `openai.api_key`. One credential object is loaded at startup and passed explicitly into raw HTTP headers and the OpenAI SDK client.

This OpenAI-key migration does **not** require changing Telegram bot-token precedence. Existing installations should preserve their local `config/config.ini`. In particular, `PreferEnvForBotToken = False` must continue to make `config/bot_token.txt` win over `TELEGRAM_BOT_TOKEN`. The upgrade overlay intentionally does not replace `config/config.ini`.

## Migration procedure

1. Sign in to the OpenAI API platform and select the intended organization and project.
2. Create a new project API key. For an unattended production bot, use a project service-account key where practical.
3. Copy the full secret immediately. Do not paste it into source code, `config.ini`, issues, chat, or Git history.
4. Replace `OPENAI_API_KEY` everywhere the bot may run:
   - shell or systemd environment;
   - Docker `.env` or orchestration secret;
   - GitHub Actions repository secret;
   - `config/api_token.txt` if the backwards-compatible file fallback is still used;
   - staging, backup, and secondary deployments.
5. Restart or redeploy every process and container.
6. Verify the replacement:

```bash
python3 scripts/verify_openai_key.py --live-request
```

The verifier prints only the key source and a short SHA-256 fingerprint. It never prints the key. The live check sends one tiny Chat Completions request and may incur a negligible charge.

A no-generation model-list check is also available:

```bash
python3 scripts/verify_openai_key.py
```

A restricted key must permit whichever endpoints are enabled. ChatKeke may use Chat Completions, audio transcription, and model-list access depending on configuration and which verification mode is used.

7. Test a normal Telegram message, a tool/function call, and speech-to-text when enabled.
8. Revoke the legacy user key only after every deployment passes.
9. Exercise every deployment once more after revocation to expose any stale secret or fallback file.

## Secret locations

### Environment or systemd

Set the new value as `OPENAI_API_KEY` in the real service environment. Avoid placing the literal secret in shell history.

### Docker

```bash
./docker_setup.sh
sudo ./docker_deploy.sh
```

The setup script hides key entry and writes `.env` with mode `0600`.

### Local fallback file

The supported fallback is `config/api_token.txt`. The environment variable is preferred. If the file is used:

```bash
chmod 600 config/api_token.txt
```

### GitHub Actions

Replace the repository secret named `OPENAI_API_KEY`. Editing a local `.env` does not update GitHub Actions.

Never commit the old or replacement key to this public repository.
