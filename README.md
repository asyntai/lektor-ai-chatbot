# lektor-ai-chatbot

Add the [Asyntai](https://asyntai.com) AI chat assistant to your Lektor site.
It answers visitor questions from your own content, day and night.

## Install

```bash
lektor plugins add lektor-ai-chatbot
```

Then create the file `configs/ai-chatbot.ini` in your project:

```ini
widget_id = asyntai_1a2b3c4d5e6f
```

Build the site. The chat bubble is on every page.

## Where the widget ID comes from

Open the Install page in your [Asyntai dashboard](https://asyntai.com/dashboard).
The widget ID is the value of `data-asyntai-id` in the snippet shown there. It
starts with `asyntai_`.

Creating an account is free, and the Free plan is enough to try the widget.

## Options

All options go in `configs/ai-chatbot.ini`.

| Option | Default | What it does |
| --- | --- | --- |
| `widget_id` | required | Your Asyntai widget ID |
| `enable_on_server` | `true` | Set to `false` to keep the widget off the site during `lektor server` |
| `script_url` | the Asyntai CDN | Advanced. Load the widget from another URL |

A missing or malformed `widget_id` stops the build with a message that says how
to fix it.

## What the plugin does

- It adds one `<script>` tag in front of the closing body tag of every HTML
  page that Lektor builds, including paginated pages and the 404 page.
- It marks the tag `async`, so your pages render first.
- It changes nothing else. No templates are overridden and no CSS is added.
- Feeds, sitemaps, CSS and images stay as they are. An HTML file in `assets/`
  gets the widget only when it is a full page.
- If a page already has the Asyntai snippet, for example in a template, the
  plugin leaves that page alone.

## Answering from your content

Asyntai reads your published pages. Add your site URL in the dashboard, and the
assistant answers from the same pages the widget sits on. You can also add
documents, and question and answer pairs.

## Removing it

Run `lektor plugins remove lektor-ai-chatbot` and build again. The widget is
gone.

## Support

Email [hello@asyntai.com](mailto:hello@asyntai.com), or read the
[Lektor guide](https://asyntai.com/documentation/integrations/lektor/).

## Licence

MIT. See [LICENSE](https://github.com/asyntai/lektor-ai-chatbot/blob/main/LICENSE).
