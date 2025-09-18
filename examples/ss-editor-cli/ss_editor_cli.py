import click
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FIRECRAWL_SCREENSHOT_URL = "https://api.firecrawl.dev/v0/scrape"
GEMINI_IMAGE_EDIT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent"

@click.command()
@click.argument('url')
def main(url):
    """Capture a website screenshot and edit it using Gemini 2.5 Flash."""
    if not FIRECRAWL_API_KEY or not GEMINI_API_KEY:
        click.echo("Set FIRECRAWL_API_KEY and GEMINI_API_KEY environment variables.")
        return

    # Capture screenshot with Firecrawl
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "url": url,
        "pageOptions": {
            "onlyMainContent": True,
            "includeHtml": True,
            "includeRawHtml": True,
            "screenshot": True,
            "waitFor": 5000
        }
    }
    click.echo("Capturing screenshot...")
    resp = httpx.post(FIRECRAWL_SCREENSHOT_URL, json=payload, headers=headers, timeout=60.0)
    resp.raise_for_status()
    firecrawl_json = resp.json()
    img_url = None
    try:
        img_url = firecrawl_json["data"]["metadata"]["screenshot"]
    except (KeyError, IndexError, TypeError):
        pass
    if not img_url:
        click.echo("Failed to get screenshot URL from Firecrawl.")
        return
    img_data = httpx.get(img_url).content
    with open("screenshot.png", "wb") as f:
        f.write(img_data)

    # Send to Gemini for creative editing
    click.echo("Editing screenshot with Gemini...")
    gemini_headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    import base64
    img_b64 = base64.b64encode(img_data).decode()
    gemini_payload = {
        "contents": [
            {"parts": [
                {"text": (
                    "Transform this website screenshot into a visually stunning, imaginative artwork. "
                    "You can reimagine the site as a futuristic cityscape, a vibrant painting, or a surreal digital landscape. "
                    "Be bold and creative—change the style, colors, and mood, and make it look like a piece of digital art rather than a plain screenshot."
                )},
                {"inline_data": {"mime_type": "image/png", "data": img_b64}}
            ]}
        ]
    }
    gemini_resp = httpx.post(GEMINI_IMAGE_EDIT_URL, headers=gemini_headers, params=params, json=gemini_payload, timeout=60.0)
    gemini_resp.raise_for_status()
    candidates = gemini_resp.json().get("candidates", [])
    if not candidates:
        click.echo("No edited image returned from Gemini.")
        return
   
    parts = candidates[0]["content"]["parts"]
    edited_img_b64 = None
    for part in parts:
        if "inlineData" in part and part["inlineData"].get("mimeType") == "image/png":
            edited_img_b64 = part["inlineData"]["data"]
            break
    if not edited_img_b64:
        click.echo("No image data found in Gemini response.")
        return
    import base64
    edited_img = base64.b64decode(edited_img_b64)
    out_path = "edited_screenshot.png"
    with open(out_path, "wb") as f:
        f.write(edited_img)
    click.echo(f"Edited image saved to {out_path}")

if __name__ == "__main__":
    main()
