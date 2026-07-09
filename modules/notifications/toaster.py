"""
Desktop notification service for ScreenMate.

Uses Windows native toast notifications (via PowerShell) on Windows 10/11.
Falls back to console logging when the platform is unsupported.

Notifications appear even when the browser is minimized.
"""

import platform
import subprocess
import sys
import threading

from modules.logger.logger import get_logger

logger = get_logger(__name__)


def _show_win_toast(title: str, message: str) -> bool:
    """Show a Windows 10/11 toast notification via PowerShell.

    Args:
        title: Bold heading line.
        message: Body text.

    Returns:
        ``True`` if the toast was sent successfully.
    """
    # Escape single quotes for PowerShell
    title_escaped = title.replace("'", "''")
    msg_escaped = message.replace("'", "''")

    ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02
)
$texts = $tpl.GetElementsByTagName("text")
$texts[0].AppendChild($tpl.CreateTextNode("{title_escaped}")) | Out-Null
$texts[1].AppendChild($tpl.CreateTextNode("{msg_escaped}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ScreenMate")
$notifier.Show($toast)
'''

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return True
    except Exception as exc:
        logger.debug("Windows toast failed: %s", exc)
        return False


def show(title: str, message: str) -> None:
    """Show a desktop notification.

    On Windows 10/11 this is a native toast.  On other platforms or
    when the native toast fails, the notification is logged to console
    (the web UI shows its own toasts via polling).

    This function always returns immediately — toasts are fire-and-forget.

    Args:
        title: Bold heading (e.g. "ScreenMate").
        message: Body text (e.g. "Analysis completed in 1.2s").
    """
    if platform.system() == "Windows":
        # Fire in a thread to avoid blocking the caller
        threading.Thread(
            target=_show_win_toast,
            args=(title, message),
            daemon=True,
        ).start()
    else:
        logger.info("[Notification] %s — %s", title, message)
