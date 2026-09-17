"""Edit one image with the Gemini image model, keeping everything the instruction does not name.

    python edit_image.py <in.jpg> <out.jpg> "<instruction>" [--size 2K] [--model gemini-3.1-flash-image]

Direct call (references only; scenes stay on the batch API). Reads GEMINI_API_KEY.
"""
import base64, json, os, sys, urllib.request

argv = sys.argv[1:]
size, model, pos = "2K", "gemini-3.1-flash-image", []
i = 0
while i < len(argv):
    if argv[i] == "--size":
        size = argv[i + 1]; i += 2
    elif argv[i] == "--model":
        model = argv[i + 1]; i += 2
    else:
        pos.append(argv[i]); i += 1
src, dst, instr = pos[0], pos[1], pos[2]
data = open(src, "rb").read()
mime = "image/png" if data[1:4] == b"PNG" else "image/jpeg"
body = {"contents": [{"parts": [{"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode()}},
                                {"text": instr}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"imageSize": size}}}
req = urllib.request.Request(
    "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
    data=json.dumps(body).encode(),
    headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=300))
for part in resp["candidates"][0]["content"]["parts"]:
    inl = part.get("inlineData") or part.get("inline_data")
    if inl:
        raw = base64.b64decode(inl["data"])
        open(dst, "wb").write(raw)
        print("wrote", dst, len(raw), "bytes")
        break
else:
    print(json.dumps(resp)[:600])
    sys.exit("no image in the response")
