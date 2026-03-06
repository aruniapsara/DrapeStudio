"""WhatsApp share link generation and message templates."""

import urllib.parse


class WhatsAppService:
    """Generate WhatsApp share links and pre-filled messages."""

    def generate_share_link(self, phone: str, message: str) -> str:
        """
        Generate a wa.me link with a pre-filled message for a specific recipient.
        `phone` should be E.164 without '+', e.g. '94771234567'.
        """
        encoded = urllib.parse.quote(message)
        clean_phone = phone.lstrip("+")
        return f"https://wa.me/{clean_phone}?text={encoded}"

    def generate_open_link(self, message: str) -> str:
        """Generate a wa.me link with no recipient (user picks contact)."""
        encoded = urllib.parse.quote(message)
        return f"https://wa.me/?text={encoded}"

    def generate_catalogue_message(self, business_name: str, page_url: str) -> str:
        """Pre-filled WhatsApp message for sharing a catalogue image."""
        return (
            f"🛍️ New arrivals from {business_name}!\n\n"
            "Check out our latest products with professional photography.\n\n"
            f"{page_url}\n\n"
            "Generated with DrapeStudio — AI Product Photography"
        )

    def generate_fiton_message(self, recommended_size: str, fit_confidence: int, link: str) -> str:
        """Pre-filled WhatsApp message for sharing a virtual fit-on result with a customer."""
        return (
            f"👗 Virtual Fit-On Result\n\n"
            f"Here's how the garment would look on you!\n"
            f"✅ Recommended size: {recommended_size}\n"
            f"📏 Fit confidence: {fit_confidence}%\n\n"
            f"View your preview: {link}\n\n"
            "— Powered by DrapeStudio"
        )

    def social_share_urls(self, page_url: str) -> dict:
        """Return share URLs for WhatsApp and Facebook."""
        encoded = urllib.parse.quote(page_url)
        return {
            "whatsapp": f"https://wa.me/?text={encoded}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded}",
        }


whatsapp_service = WhatsAppService()
