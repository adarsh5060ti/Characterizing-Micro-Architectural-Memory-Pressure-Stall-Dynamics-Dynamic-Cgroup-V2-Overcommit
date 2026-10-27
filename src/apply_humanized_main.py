#!/usr/bin/env python3
"""
apply_humanized_main.py - Apply humanized content from Downloads/main.tex to paper/main.tex,
preserving all figure paths, environments, references, and styling.
"""

import os
import re
import shutil
import subprocess
import pypdf

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dl_file = r"c:\Users\Adarsh Singh\Downloads\main.tex"
    paper_tex = os.path.join(root_dir, "paper", "main.tex")
    tectonic = os.path.join(root_dir, "bin", "tectonic.exe")

    # 1. Sync tables into paper/tables/ to ensure both relative and absolute paths resolve
    os.makedirs(os.path.join(root_dir, "paper", "tables"), exist_ok=True)
    for f in os.listdir(os.path.join(root_dir, "tables")):
        if f.endswith(".tex"):
            shutil.copy2(os.path.join(root_dir, "tables", f), os.path.join(root_dir, "paper", "tables", f))

    with open(dl_file, "r", encoding="utf-8") as f:
        dl_content = f.read()

    # 2. Preamble path setup
    preamble_addition = """\\usepackage{graphicx}
\\graphicspath{{../figures/}{figures/}}
\\makeatletter
\\def\\input@path{{../tables/}{tables/}}
\\makeatother"""

    dl_content = dl_content.replace("\\usepackage{graphicx}", preamble_addition, 1)

    # 3. Normalize includegraphics and table inputs
    dl_content = re.sub(r'\\includegraphics\[([^\]]*)\]\{figures/(fig\d+\.pdf)\}', r'\\includegraphics[\1]{\2}', dl_content)
    dl_content = re.sub(r'\\input\{tables/(tab\d+_[^}]+\.tex)\}', r'\\input{\1}', dl_content)

    # 4. Replace QLATEX tokens
    # Line 110: table~QLATEXz0000q -> Table~\ref{tab:taxonomy}
    dl_content = dl_content.replace("table~QLATEXz0000q", "Table~\\ref{tab:taxonomy}")

    # Line 355:
    dl_content = dl_content.replace("Tier 3 QLATEXz0006q", r"Tier 3 \texttt{memory.high}")
    dl_content = dl_content.replace("(QLATEXz0000q to QLATEXz0001q in Fig.~QLATEXz0005q)", r"($t = 35\text{s}$ to $75\text{s}$ in Fig.~\ref{fig:timeseries})")
    dl_content = dl_content.replace("kernel QLATEXz0007q spinlocks", r"kernel \texttt{shrink\_node()} spinlocks")
    dl_content = dl_content.replace("Tier 3 is sustaining QLATEXz0002q average bandwidth", r"Tier 3 is sustaining $4,159.2\text{ MB/s}$ average bandwidth")
    dl_content = dl_content.replace("(QLATEXz0003q of unconstrained's QLATEXz0004q)", r"($99.7\%$ of unconstrained's $4,171.2\text{ MB/s}$)")

    # Line 390:
    dl_content = dl_content.replace("Across the thresholds QLATEXz0000q, to verify our parametric tail formulation, Figure~QLATEXz0004q(a) is offering the empirical Mean Residual Life (MRL) plot", "Across the thresholds $u \\in [20, 80]\\ \\mu\\text{s}$, to verify our parametric tail formulation, Figure~\\ref{fig:evt_diag}(a) is offering the empirical Mean Residual Life (MRL) plot")
    dl_content = dl_content.replace("figure~QLATEXz0005q(b) is plotting the complementary cumulative distribution function (CCDF) on log-log axes for QLATEXz0001q", "Figure~\\ref{fig:evt_diag}(b) is plotting the complementary cumulative distribution function (CCDF) on log-log axes for $\\Omega = 1.6$")
    dl_content = dl_content.replace("fitted Fr{\\'e}chet-class GPD curve (QLATEXz0002q)", "fitted Fr{\\'e}chet-class GPD curve ($\\hat{\\xi} = 0.382, \\hat{\\sigma} = 5,374.0\\ \\mu\\text{s}$)")
    dl_content = dl_content.replace("linearity is established for QLATEXz0003q", "linearity is established for $u \\ge 35\\ \\mu\\text{s}$")

    # 5. Restore authoritative Springer Declarations block
    with open(paper_tex, "r", encoding="utf-8") as f:
        orig_content = f.read()

    orig_decl = orig_content[orig_content.find("\\section*{Declarations}"):orig_content.find("\\bibliography")]
    dl_decl_start = dl_content.find("\\bmhead{Declarations}")
    dl_decl_end = dl_content.find("\\bibliography")
    if dl_decl_start != -1 and dl_decl_end != -1:
        dl_content = dl_content[:dl_decl_start] + orig_decl + dl_content[dl_decl_end:]

    # Verify no QLATEX left
    remaining_qlatex = re.findall(r"QLATEX\w*", dl_content)
    if remaining_qlatex:
        raise ValueError(f"Found remaining QLATEX tokens: {remaining_qlatex}")
    print("Zero QLATEX tokens verified.")

    # 6. Write to paper/main.tex
    with open(paper_tex, "w", encoding="utf-8") as f:
        f.write(dl_content)
    print("Updated paper/main.tex successfully.")

    # 7. Compile paper/main.tex with Tectonic
    print("Compiling paper/main.tex with Tectonic...")
    res = subprocess.run([tectonic, "-X", "compile", "paper/main.tex"], cwd=root_dir, capture_output=True, text=True)
    if res.returncode != 0:
        print("Tectonic Compilation ERROR:")
        print(res.stderr[:2000])
        return False
    else:
        print("Tectonic compilation SUCCESSFUL (0 errors)!")

    # 8. Check PDF for broken references
    pdf_path = os.path.join(root_dir, "paper", "main.pdf")
    if os.path.exists(pdf_path):
        reader = pypdf.PdfReader(pdf_path)
        print(f"Generated PDF pages: {len(reader.pages)}")
        broken = []
        for idx, page in enumerate(reader.pages):
            txt = page.extract_text()
            if "??" in txt or "[?]" in txt:
                broken.append(idx + 1)
        if broken:
            print(f"WARNING: Broken references found on pages: {broken}")
        else:
            print("PDF Verification: 0 broken references (?? / [?])!")

    return True

if __name__ == "__main__":
    main()
