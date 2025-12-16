from flask import Flask, request, send_file, render_template_string
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
import io
import openai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

# ---------------- Configuration ----------------
app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")  # Use environment variable

# ---------------- HTML Template ----------------
html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF Tools</title>
<style>
body { font-family: Arial, sans-serif; margin:0; padding:0; background:#f5f6fa; }
header { background:#2f3640; color:white; padding:20px; text-align:center; }
.container { padding:20px; max-width:500px; margin:auto; }
h2 { color:#2f3640; }
form { background:white; padding:15px; margin-bottom:20px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.2);}
input[type=file], input[type=text] { width:100%; margin-bottom:10px; padding:8px; }
button { background:#44bd32; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; width:100%; font-size:16px;}
button:hover { background:#4cd137; }
a { color:#40739e; text-decoration:none; }
a:hover { text-decoration:underline; }
</style>
</head>
<body>
<header>
<h1>PDF Tools Website</h1>
<p>Merge, Split, Image→PDF, AI Summarization, Sign & Edit PDFs</p>
</header>
<div class="container">
    <h2>Merge PDFs</h2>
    <form method="POST" action="/merge" enctype="multipart/form-data">
        <input type="file" name="pdfs" multiple required>
        <button type="submit">Merge</button>
    </form>

    <h2>Split PDF</h2>
    <form method="POST" action="/split" enctype="multipart/form-data">
        <input type="file" name="pdf" required>
        <button type="submit">Split</button>
    </form>

    <h2>Image to PDF</h2>
    <form method="POST" action="/image_to_pdf" enctype="multipart/form-data">
        <input type="file" name="image" required>
        <button type="submit">Convert</button>
    </form>

    <h2>Sign PDF</h2>
    <form method="POST" action="/sign_pdf" enctype="multipart/form-data">
        <input type="file" name="pdf" required>
        <input type="file" name="signature" accept="image/*" required>
        <button type="submit">Sign PDF</button>
    </form>

    <h2>Edit PDF Text</h2>
    <form method="POST" action="/edit_pdf" enctype="multipart/form-data">
        <input type="file" name="pdf" required>
        <input type="text" name="text" placeholder="Enter text to add" required>
        <button type="submit">Add Text</button>
    </form>

    <h2>AI PDF Summarization</h2>
    <form method="POST" action="/ai" enctype="multipart/form-data">
        <input type="file" name="pdf" required>
        <button type="submit">Summarize</button>
    </form>
</div>
</body>
</html>
'''

# ---------------- Homepage ----------------
@app.route("/")
def home():
    return render_template_string(html_template)

# ---------------- Merge PDFs ----------------
@app.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("pdfs")
    merger = PdfMerger()
    for f in files:
        merger.append(f)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return send_file(output, download_name="merged.pdf", as_attachment=True)

# ---------------- Split PDF ----------------
@app.route("/split", methods=["POST"])
def split():
    file = request.files['pdf']
    reader = PdfReader(file)
    output_files = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out_io = io.BytesIO()
        writer.write(out_io)
        out_io.seek(0)
        output_files.append((f'page_{i+1}.pdf', out_io))
    if len(output_files) == 1:
        return send_file(output_files[0][1], download_name=output_files[0][0], as_attachment=True)
    import zipfile
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode="w") as zf:
        for name, file_io in output_files:
            zf.writestr(name, file_io.read())
    zip_io.seek(0)
    return send_file(zip_io, download_name="split_pages.zip", as_attachment=True)

# ---------------- Image to PDF ----------------
@app.route("/image_to_pdf", methods=["POST"])
def image_to_pdf():
    file = request.files['image']
    image = Image.open(file).convert("RGB")
    output = io.BytesIO()
    image.save(output, format="PDF")
    output.seek(0)
    return send_file(output, download_name="converted.pdf", as_attachment=True)

# ---------------- Sign PDF ----------------
@app.route("/sign_pdf", methods=["POST"])
def sign_pdf():
    pdf_file = request.files['pdf']
    sig_file = request.files['signature']
    reader = PdfReader(pdf_file)
    writer = PdfWriter()
    sig_image = Image.open(sig_file).convert("RGB")
    sig_pdf_io = io.BytesIO()
    sig_image.save(sig_pdf_io, format="PDF")
    sig_pdf_io.seek(0)
    sig_reader = PdfReader(sig_pdf_io)
    for i, page in enumerate(reader.pages):
        writer.add_page(page)
        if i == 0:
            writer.pages[i].merge_page(sig_reader.pages[0])
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return send_file(output, download_name="signed.pdf", as_attachment=True)

# ---------------- Edit PDF Text ----------------
@app.route("/edit_pdf", methods=["POST"])
def edit_pdf():
    file = request.files['pdf']
    text_to_add = request.form['text']
    reader = PdfReader(file)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    overlay_io = io.BytesIO()
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    c = canvas.Canvas(overlay_io, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, text_to_add)
    c.save()
    overlay_io.seek(0)
    overlay_reader = PdfReader(overlay_io)
    for i in range(len(writer.pages)):
        writer.pages[i].merge_page(overlay_reader.pages[0])
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return send_file(output, download_name="edited.pdf", as_attachment=True)

# ---------------- AI PDF Summarization ----------------
@app.route("/ai", methods=["POST"])
def ai():
    file = request.files['pdf']
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    if not text.strip():
        return "PDF has no text. AI summarization requires text PDFs."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":f"Summarize this PDF content:\n{text}"}]
    )
    summary = response.choices[0].message.content
    return f"<h2>PDF Summary:</h2><p>{summary}</p><a href='/'>Back</a>"

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)