import { useCallback, useEffect, useState } from 'react';

export function useKioskMode() {
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const onFsChange = useCallback(() => {
    const fsEl = document.fullscreenElement || (document as any).webkitFullscreenElement;
    setIsFullscreen(!!fsEl);
    document.body.classList.toggle('kiosk', !!fsEl);
  }, []);

  useEffect(() => {
    document.addEventListener('fullscreenchange', onFsChange);
    (document as any).addEventListener?.('webkitfullscreenchange', onFsChange);

    // Basic kiosk hardening: disable context menu, text selection, and key combos
    const preventCtx = (e: Event) => e.preventDefault();
    const preventSelect = (e: Event) => e.preventDefault();
    const preventKey = (e: KeyboardEvent) => {
      // Block ESC from leaving fullscreen, F11, Ctrl+W, Ctrl+L, Ctrl+R, Alt+Tab can't be blocked.
      // Note: Browser limitations apply; this only affects some combos.
      const k = e.key?.toLowerCase();
      if (k === 'f11' || k === 'f5' || k === 'escape' || (e.ctrlKey && ['w','r','l','t','n'].includes(k))) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    window.addEventListener('contextmenu', preventCtx);
    document.addEventListener('selectstart', preventSelect);
    document.addEventListener('dragstart', preventSelect);
    window.addEventListener('keydown', preventKey, { capture: true });

    return () => {
      document.removeEventListener('fullscreenchange', onFsChange);
      (document as any).removeEventListener?.('webkitfullscreenchange', onFsChange);
      window.removeEventListener('contextmenu', preventCtx);
      document.removeEventListener('selectstart', preventSelect);
      document.removeEventListener('dragstart', preventSelect);
      window.removeEventListener('keydown', preventKey, { capture: true } as any);
      document.body.classList.remove('kiosk');
    };
  }, [onFsChange]);

  const enterFullscreen = useCallback(async () => {
    const el = document.documentElement as any;
    if (el.requestFullscreen) await el.requestFullscreen();
    else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen();
  }, []);

  const exitFullscreen = useCallback(async () => {
    const doc = document as any;
    if (document.fullscreenElement || doc.webkitFullscreenElement) {
      if (document.exitFullscreen) await document.exitFullscreen();
      else if (doc.webkitExitFullscreen) await doc.webkitExitFullscreen();
    }
  }, []);

  return { isFullscreen, enterFullscreen, exitFullscreen };
}

export default useKioskMode;
