# ULTRON iPhone capabilities

## Implemented in this change

The chat can use native iOS features after the user taps a control:
- Copy an assistant response to the system clipboard.
- Read a response aloud with the built-in Brazilian Portuguese speech voice.
- Stop speech playback.

These features run on-device and do not send the response to another AI provider.

## Permission and platform boundaries

ULTRON is an ordinary iOS app. iOS does not allow an app to silently take unrestricted control of the device, read arbitrary app data, press buttons in other apps, bypass the lock screen, or execute arbitrary shell commands. Those capabilities are not promised.

Broader integrations must use Apple's supported APIs and explicit permission flows:
- App Intents / Shortcuts for user-invoked workflows.
- EventKit for calendar and reminders, after system permission.
- CoreLocation only after location permission.
- Photos picker for user-selected images.
- URL opening only for HTTPS destinations and after a user tap.
- Notifications only after notification authorization.

## Security rules

- No remote instruction may execute a device action silently.
- Destructive, financial, communication, account, or privacy-sensitive actions require a clear confirmation screen.
- Never place a server-wide secret inside the IPA.
- Keep personal data on-device unless the user explicitly chooses a feature that needs transmission.
- Do not use Accessibility APIs to automate other apps or bypass iOS protections.
- Every new device capability requires a UI affordance, permission rationale, denial handling, and tests.

## Validation still required

The iOS GitHub Actions workflow must compile this change. A successful CI build does not replace installation and testing on the user's iPhone 11 Pro.
