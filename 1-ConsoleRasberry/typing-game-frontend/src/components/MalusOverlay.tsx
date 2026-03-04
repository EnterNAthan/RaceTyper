import React from 'react';

// ── Intrusive GIF URLs (cycle through them for variety) ──
// Place your .gif files in the public/ folder, they'll be served at the root.
const INTRUSIVE_GIFS = [
    '/malus1.gif',
    '/malus2.gif',
    '/malus3.gif',
];

let gifIndex = 0;
function nextGif(): string {
    const url = INTRUSIVE_GIFS[gifIndex % INTRUSIVE_GIFS.length];
    gifIndex++;
    return url;
}

interface MalusOverlayProps {
    /** Whether the fullscreen intrusive GIF is currently active */
    showGif: boolean;
    /** Whether keyboard input is currently disabled */
    keyboardDisabled: boolean;
}

/**
 * Renders fullscreen malus overlays on top of the game UI.
 *
 * - **Intrusive GIF**: covers the entire screen for 3 seconds with an
 *   animated GIF so the player can't see the phrase.
 * - **Keyboard disabled**: shows a subtle banner so the player knows
 *   their input is frozen for 1 second.
 */
const MalusOverlay: React.FC<MalusOverlayProps> = ({ showGif, keyboardDisabled }) => {
    return (
        <>
            {/* ── Intrusive GIF overlay ── */}
            {showGif && (
                <div className="malus-gif-overlay" aria-live="assertive">
                    <img
                        src={nextGif()}
                        alt="Malus!"
                        className="malus-gif-image"
                    />
                    <span className="malus-gif-label">MALUS !</span>
                </div>
            )}

            {/* ── Keyboard disabled banner ── */}
            {keyboardDisabled && (
                <div className="malus-kb-overlay" aria-live="assertive">
                    <div className="malus-kb-box">
                        <span className="malus-kb-icon">⌨️</span>
                        <span className="malus-kb-text">Clavier désactivé !</span>
                    </div>
                </div>
            )}
        </>
    );
};

export default MalusOverlay;
