**RabbitStream WASM extractor**

This tool extracts the video sources from RabbitStream embeds. It is designed for use in projects like anime/video extractors where RabbitStream is used as a streaming provider.

## Usage

Use `ts-node` to run `rabbit.ts`.

### Example:

```bash
ts-node rabbit.ts "<embed_url>" "<referer_site>"
```

* **`<embed_url>`**: The RabbitStream embed URL to extract from.
* **`<referer_site>`**: The domain to send as the HTTP referer (e.g., `https://hianime.to`).

The script will return a JSON object containing video sources and available subtitles/tracks.

## Binaries

Platform-specific precompiled binaries are available in the [releases](https://github.com/pratikpatel8982/yt-dlp-hianime/releases) section.

These are used automatically by the Python extractor if the appropriate binary is present or downloaded.

---

## Credits

This project is based on the original work from [drblgn/rabbit\_wasm](https://github.com/drblgn/rabbit_wasm).
Full credit to the original author for the WebAssembly-based RabbitStream reverse-engineering and extraction logic.

---

Let me know if you'd like to include build instructions for the binaries or usage within your Python extractor too.
