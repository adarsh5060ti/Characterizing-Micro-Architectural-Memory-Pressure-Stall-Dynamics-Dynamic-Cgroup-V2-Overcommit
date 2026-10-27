#!/usr/bin/env python3
"""
build_humanizer_safe_package.py - Build modular, humanizer-safe Overleaf zip package.
Extracts updated sections from paper/main.tex, verifies compilation, and packages for Overleaf.
"""

import os
import zipfile
import shutil
import subprocess
import pypdf

def build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modular_dir = os.path.join(root_dir, "modular_package")
    figures_src = os.path.join(root_dir, "figures")
    tables_src = os.path.join(root_dir, "tables")
    bib_src = os.path.join(root_dir, "literature", "peer_reviewed_papers.bib")
    paper_tex = os.path.join(root_dir, "paper", "main.tex")
    sections_dir = os.path.join(modular_dir, "sections")
    os.makedirs(sections_dir, exist_ok=True)
    readme_path = os.path.join(modular_dir, "README_HOW_TO_HUMANIZE_WITHOUT_ERRORS.txt")

    print("=================================================================")
    print(" [MODULAR PACKAGE BUILD] Syncing and splitting sections...")
    print("=================================================================")

    # 1. Sync updated figures
    mod_fig_dir = os.path.join(modular_dir, "figures")
    os.makedirs(mod_fig_dir, exist_ok=True)
    fig_count = 0
    for f in os.listdir(figures_src):
        if f.endswith(".pdf"):
            shutil.copy2(os.path.join(figures_src, f), os.path.join(mod_fig_dir, f))
            fig_count += 1
    print(f" -> Synchronized {fig_count} figures to modular_package/figures/")

    # 2. Sync updated tables
    mod_tab_dir = os.path.join(modular_dir, "tables")
    os.makedirs(mod_tab_dir, exist_ok=True)
    tab_count = 0
    for f in os.listdir(tables_src):
        if f.endswith(".tex"):
            shutil.copy2(os.path.join(tables_src, f), os.path.join(mod_tab_dir, f))
            tab_count += 1
    print(f" -> Synchronized {tab_count} tables to modular_package/tables/")

    # 3. Sync bibliography
    if os.path.exists(bib_src):
        shutil.copy2(bib_src, os.path.join(modular_dir, "peer_reviewed_papers.bib"))
        print(" -> Synchronized peer_reviewed_papers.bib")

    # 4. Split paper/main.tex into sections/*.tex
    with open(paper_tex, "r", encoding="utf-8") as f:
        paper_text = f.read()

    section_defs = [
        (r"\section{Introduction}", "01_introduction.tex"),
        (r"\section{PRISMA-2020 Systematic Literature Taxonomy and Gap Analysis}", "02_literature_taxonomy.tex"),
        (r"\section{Mathematical Model of Cgroup V2 Pressure Dynamics and Extreme Value Tails}", "03_pressure_dynamics_model.tex"),
        (r"\section{PSI-Shed Proactive Acceleration-Aware Memory Controller}", "04_psi_shed_controller.tex"),
        (r"\section{Experimental Methodology and Heterogeneous Workload Testbed}", "05_experimental_methodology.tex"),
        (r"\section{Empirical Results and Parametric Statistical Analysis}", "06_empirical_results.tex"),
        (r"\section{Controller Overhead, Sensitivity, and Ablation Analysis}", "07_overhead_and_ablation.tex"),
        (r"\section{Threats to Validity and Production Deployment Guidelines}", "08_threats_to_validity.tex"),
        (r"\section{Conclusion}", "09_conclusion.tex"),
        (r"\section*{Declarations}", "10_declarations.tex"),
        (r"\bibliography{peer_reviewed_papers}", None)
    ]

    indices = []
    for header, fname in section_defs:
        pos = paper_text.find(header)
        if pos == -1:
            raise ValueError(f"Header not found in paper/main.tex: {header}")
        indices.append(pos)

    for i in range(len(section_defs) - 1):
        fname = section_defs[i][1]
        sec_content = paper_text[indices[i]:indices[i+1]].strip() + "\n"
        sec_path = os.path.join(sections_dir, fname)
        with open(sec_path, "w", encoding="utf-8") as f:
            f.write(sec_content)
        print(f" -> Generated sections/{fname} ({len(sec_content)} chars)")

    # 5. README instructions
    readme_content = """================================================================================
  HOW TO HUMANIZE / CONVERT PROSE WITHOUT CAUSING OVERLEAF COMPILATION ERRORS
================================================================================

Why Overleaf throws errors after using AI humanizers (e.g., Undetectable AI, QuillBot):
  1. Automated tools do not understand LaTeX syntax: they mangle table rows (& and \\\\), 
     causing fatal 'Misplaced \\noalign' errors.
  2. Automated tools frequently break math delimiters ($ ... $), citation keys (\\cite{...}), 
     and cross-references (\\ref{...}).
  3. Putting a monolithic main.tex with preamble and packages into a paraphraser destroys 
     document structure.

HOW THIS MODULAR PACKAGE SOLVES THIS COMPLETELY:
  - 'main.tex' is protected and contains only the preamble, metadata, and \\input commands.
  - Tables are safely isolated in the 'tables/' folder.
  - All paper prose is neatly split into individual files inside the 'sections/' folder:
      * sections/01_introduction.tex
      * sections/02_literature_taxonomy.tex
      * sections/03_pressure_dynamics_model.tex
      * sections/04_psi_shed_controller.tex
      * sections/05_experimental_methodology.tex
      * sections/06_empirical_results.tex
      * sections/07_overhead_and_ablation.tex
      * sections/08_threats_to_validity.tex
      * sections/09_conclusion.tex
      * sections/10_declarations.tex

THE 3 GOLDEN RULES FOR 100% ERROR-FREE HUMANIZING:
  Rule 1: ONLY convert the prose paragraphs inside 'sections/*.tex'.
          Never paste 'main.tex' or files from 'tables/' into a paraphraser.
  Rule 2: When prompting an AI tool / humanizer, instruct it:
          "Rewrite this academic text with natural human cadence, varied sentence lengths, 
           and active voice. STRICT INVARIANT: Preserve all LaTeX tags, equations ($...$), 
           \\cite{...}, \\ref{...}, \\texttt{...}, and \\begin{...} tags exactly as written."
  Rule 3: Copy and paste back only one section at a time into Overleaf. 
          If any typo occurs, Overleaf will tell you the exact line number inside that 
          specific section file, making it instantaneous to identify and fix.
================================================================================
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 6. Compile modular_package/main.tex with Tectonic
    tectonic_bin = os.path.join(root_dir, "bin", "tectonic.exe")
    if os.path.exists(tectonic_bin):
        print(" -> Compiling modular_package/main.tex with Tectonic...")
        res = subprocess.run([tectonic_bin, "-X", "compile", "modular_package/main.tex"], cwd=root_dir, capture_output=True, text=True)
        if res.returncode != 0:
            print(f" [ERROR] Tectonic compilation failed: {res.stderr[:500]}")
        else:
            print(" -> Modular compilation SUCCESSFUL (0 errors).")
            pdf_path = os.path.join(modular_dir, "main.pdf")
            if os.path.exists(pdf_path):
                reader = pypdf.PdfReader(pdf_path)
                has_issues = False
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if "??" in t or "[?]" in t:
                        has_issues = True
                        print(f"   [WARNING] Page {idx+1} contains ?? or [?]")
                if not has_issues:
                    print(f" -> PDF Verification: Clean {len(reader.pages)} pages, 0 broken references (?? / [?]).")

    # 7. Package into ZIP Archive
    dest_dir = r"C:\Users\Adarsh Singh\Desktop\AAMMAZON"
    os.makedirs(dest_dir, exist_ok=True)
    zip_dest = os.path.join(dest_dir, "humanizer_safe_modular_overleaf.zip")
    if os.path.exists(zip_dest):
        os.remove(zip_dest)

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(modular_dir):
            for file in files:
                full = os.path.join(root, file)
                rel = os.path.relpath(full, modular_dir)
                zf.write(full, rel)

    zip_size_mb = os.path.getsize(zip_dest) / (1024 * 1024)
    print(f"=================================================================")
    print(f" [SUCCESS] Generated humanizer_safe_modular_overleaf.zip")
    print(f"   Archive Size: {zip_size_mb:.2f} MB")
    print(f"   File Count:   {len(zf.filelist)} files")
    print(f"   Location:     {zip_dest}")

    # Mirror locally
    shutil.copy2(zip_dest, os.path.join(root_dir, "humanizer_safe_modular_overleaf.zip"))
    print("=================================================================")

if __name__ == "__main__":
    build()
