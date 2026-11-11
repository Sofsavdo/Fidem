// The one place that says where "contact admin" goes (Telegram).
import { openExternalLink } from "@/lib/telegram";

export const SUPPORT_USERNAME = "Medik005";
export const SUPPORT_URL = `https://t.me/${SUPPORT_USERNAME}`;

export function openSupportChat() {
  openExternalLink(SUPPORT_URL);
}
