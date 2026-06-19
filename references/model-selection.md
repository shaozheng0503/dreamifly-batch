# Model Selection

Use `python3 dreamify.py --list-models` when the platform model list may have changed.

## Defaults

- Cheap anime or illustration batches: `Wai-SDXL-V150` or `Wai-SDXL-V170`
- Fast Chinese/general text-to-image: `Z-Image-Turbo`
- Image editing, adding elements, restyling: `Qwen-Image-Edit` with `img=`
- High-quality or complex Chinese image tasks: `gpt-image-2`
- Expensive high-end image tasks: `nano-banana-2` only after explicit approval
- One source image to video: `Wan2.2-I2V-Lightning` with exactly one `img=`
- Text-to-video or multi-reference video: `happyhorse-1.0`

## Inline Parameters

- `model=...`: choose model
- `style=cartoon|anime|oil|lineart|vector|pixel|lego|riso|realistic|puppet|emoji`
- `16:9` or `1024x768`: aspect ratio or exact dimensions
- `x2`: image batch size, max 4
- `seed=123`, `steps=20`, `neg=...`
- `img=path-or-url`: local path, URL, or data URI; comma-separated for multiple references
- `secs=5`, `res=720P`: video parameters for `happyhorse-1.0`

## Cost Guardrail

Any item estimated at 5+ credits must stop before real generation and ask the user to confirm. Treat all video models and `nano-banana-2` as high-cost.
