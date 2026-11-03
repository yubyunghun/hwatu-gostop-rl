import { AnimatePresence, motion } from "motion/react";
import type { TurnBanner as TurnBannerValue } from "../state/useGameSession";

export function TurnBanner({ who }: { who: TurnBannerValue }) {
  return (
    <div className="turn-banner-slot">
      <AnimatePresence>
        {who && (
          <motion.div
            key={who}
            className={`turn-banner turn-banner--${who}`}
            initial={{ opacity: 0, y: -10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            transition={{ duration: 0.22 }}
          >
            {who === "you" ? "Your turn" : "Opponent's turn"}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
