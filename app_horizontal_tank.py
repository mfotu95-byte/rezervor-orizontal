# app_horizontal_tank.py
# Dimensionare rezervor orizontal (cilindru + capace elipsoidale 2:1)
# Intrări grupate: Capacitate & Geometrie / Material & Mecanică / Saddle-uri & Montaj / Calibrare & Grafic
# Single-mode: utilizatorul alege D și L/D. Export = Word (DOCX) cu concluzii.

import math
import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="Rezervor orizontal - dimensionare", layout="wide")

# =========================== Funcții auxiliare ===========================
def head_volume_21_ellipsoidal(R: float) -> float:
    """Volum capac 2:1 elipsoidal: V_head = (1/3)*π*R^3"""
    return (math.pi / 3.0) * (R ** 3)

def level_segment_area(R: float, h: float) -> float:
    """Aria segmentului circular pentru înălțime h în cilindru (0..2R)."""
    if h <= 0:
        return 0.0
    if h >= 2 * R:
        return math.pi * R ** 2
    return R**2 * math.acos((R - h) / R) - (R - h) * math.sqrt(max(0.0, 2*R*h - h**2))

def make_conclusions_docx(geom: dict, mech: dict, saddles: dict) -> bytes:
    """
    Generează un DOCX cu concluzii concise: Geometrie, Verificare mecanică, Saddle-uri.
    """
    d = Document()

    # Titlu
    title = d.add_paragraph("Raport scurt – Rezervor orizontal (cilindru + capace 2:1)")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.runs[0]; run.bold = True; run.font.size = Pt(14)

    # 1) Geometrie
    d.add_heading("1) Geometrie & Capacitate", level=2)
    D_val = 2 * geom.get("R [m]", 0.0)
    p = d.add_paragraph()
    p.add_run("Diametru D: ").bold = True;                p.add_run(f"{D_val:.2f} m\n")
    p.add_run("Raport L/D: ").bold = True;                p.add_run(f"{geom.get('L/D rezultat [-]', 0.0):.2f}\n")
    p.add_run("Lungime cilindru L_cil: ").bold = True;    p.add_run(f"{geom.get('L_cil [m]', 0.0):.2f} m\n")
    p.add_run("Lungime totală L_total: ").bold = True;    p.add_run(f"{geom.get('L_total [m]', 0.0):.2f} m\n")
    p.add_run("Volum total calculat: ").bold = True;      p.add_run(f"{geom.get('V_total calc [m³]', 0.0):.2f} m³\n")
    dv = float(geom.get("ΔV [m³]", 0.0))
    p.add_run("Abatere ΔV (față de țintă): ").bold = True; p.add_run(f"{dv:+.2f} m³  ")
    p.add_run("(OK – în toleranță)" if abs(dv) <= 0.5 else "(Ajustează D / L/D pentru ΔV≈0)").italic = True

    # 2) Verificare mecanică
    d.add_heading("2) Verificare mecanică (efort cerc – hidrostatic)", level=2)
    ok_mech = (mech.get("t_disp [mm]", 0.0) >= max(mech.get("t_req [mm]", 0.0), mech.get("t_min [mm]", 0.0)))
    tbl = d.add_table(rows=2, cols=4)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    hdr[0].text = "σ utilizată [MPa]"; hdr[1].text = "t_req [mm]"
    hdr[2].text = "t_min [mm]";        hdr[3].text = "t_disp = t_nom − CA [mm]"
    row = tbl.rows[1].cells
    row[0].text = f"{mech.get('σ utilizată [MPa]', 0.0):.2f}"
    row[1].text = f"{mech.get('t_req [mm]', 0.0):.2f}"
    row[2].text = f"{mech.get('t_min [mm]', 0.0):.2f}"
    row[3].text = f"{mech.get('t_disp [mm]', 0.0):.2f}"

    verdict = d.add_paragraph()
    verdict.add_run("Verdict: ").bold = True
    verdict.add_run("OK – grosimea este suficientă" if ok_mech else "NU – crește grosimea (t_disp < max(t_req, t_min))").bold = True

    # 3) Saddle-uri
    d.add_heading("3) Saddle-uri (dispunere)", level=2)
    p2 = d.add_paragraph()
    p2.add_run("Distanță recomandată S: ").bold = True
    p2.add_run(f"{saddles.get('S_rec_min [m]', 0.0):.2f} – {saddles.get('S_rec_max [m]', 0.0):.2f} m\n")
    p2.add_run("Deschidere disponibilă L_total − 2a: ").bold = True
    p2.add_run(f"{saddles.get('Deschidere [m]', 0.0):.2f} m\n")
    p2.add_run("Alege S în intervalul recomandat și verifică S ≤ deschidere.").italic = True

    d.add_paragraph().add_run("Raport generat automat de aplicație.").italic = True

    buf = io.BytesIO()
    d.save(buf); buf.seek(0)
    return buf.read()

# =========================== Sidebar – GRUPURI ===========================
with st.sidebar:
    st.title("Date de intrare")

    # A) Capacitate & Geometrie
    with st.expander("A) Capacitate & Geometrie", expanded=True):
        V_work = st.number_input("Volum util necesar V_util [m³]", value=100.0, min_value=0.0, step=1.0)
        f_fill = st.slider("Fracție de umplere f_umplere [-]", 0.50, 1.00, 0.90, 0.01, format="%.2f")
        V_total_target = V_work / f_fill if f_fill > 0 else 0.0
        st.caption(f"Volum total de proiectare **V_total = {V_total_target:.3f} m³**")

        # Single-mode: utilizatorul setează simultan D și L/D
        colA, colB = st.columns([3, 2])
        with colA:
            L_over_D = st.slider("Raport L/D (recomandat 2–5)", 1.50, 6.00, 3.00, step=0.01, format="%.2f")
        with colB:
            L_over_D = st.number_input("L/D (tastat fin)", min_value=1.50, max_value=6.00, value=float(L_over_D), step=0.01, format="%.2f")

        D = st.number_input("Diametru D [m]", value=3.2, min_value=0.1, step=0.05, help="Diametrul poate fi limitat de transport.")
        D_max = st.number_input("Diametru maxim admis D_max [m] (opțional)", value=0.0, min_value=0.0, step=0.1, help="Lasă 0 dacă nu ai constrângere.")
        L_max = st.number_input("Lungime totală maximă L_max [m] (opțional)", value=0.0, min_value=0.0, step=0.5, help="Lasă 0 dacă nu ai constrângere.")

    # B) Material & Mecanică
    with st.expander("B) Material & Mecanică", expanded=False):
        rho = st.number_input("Densitate lichid ρ [kg/m³]", value=1000.0, min_value=1.0)
        sigma_allow = st.number_input("Tensiune admisă material σ_adm [MPa]", value=120.0, min_value=1.0)
        SF = st.number_input("Factor siguranță SF [-]", value=1.5, min_value=1.0)
        t_min = st.number_input("Grosime minimă de fabricație t_min [mm]", value=6.0, min_value=0.0, step=0.5)
        CA = st.number_input("Adaos de coroziune CA [mm]", value=1.0, min_value=0.0, step=0.5)
        t_nom = st.number_input("Grosime nominală aleasă t_nom [mm]", value=8.0, min_value=0.0, step=0.5)

    # C) Saddle-uri & Montaj
    with st.expander("C) Saddle-uri & Montaj", expanded=False):
        a = st.number_input("Distanță de la tangentă la centrul saddle a [m]", value=0.2, min_value=0.0, step=0.05)
        S_user = st.number_input("S ales (span centru–centru) [m] (opțional)", value=0.0, min_value=0.0, step=0.05,
                                 help="Poți lăsa 0 și vei vedea intervalul recomandat în tab-ul Saddle-uri.")

    # D) Calibrare & Grafic
    with st.expander("D) Calibrare & Grafic", expanded=False):
        n_points = st.slider("Număr puncte pe curba nivel–volum", 20, 300, 120, 5)

# =========================== Calcul Geometrie ===========================
R = D / 2.0
h_head = D / 4.0                 # 2:1 elipsoidal
L_total = L_over_D * D
L_cyl = max(0.0, L_total - 2.0 * h_head)
V_head = head_volume_21_ellipsoidal(R)
V_cyl = math.pi * R**2 * L_cyl
V_total_calc = V_cyl + 2.0 * V_head
dV = V_total_calc - V_total_target
L_over_D_calc = L_total / D if D > 0 else 0.0

# check-uri geometrice
warn_D = (D_max > 0) and (D > D_max)
warn_L = (L_max > 0) and (L_total > L_max)

# =========================== Tabs UI ===========================
tab_geom, tab_lv, tab_mech, tab_sad = st.tabs(
    ["Geometrie", "Nivel–Volum", "Verificare mecanică", "Saddle-uri"]
)

# -------- Geometrie --------
with tab_geom:
    st.subheader("Geometrie & Capacitate")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rază R [m]", f"{R:.3f}")
    c2.metric("Adâncime capac h_cap [m]", f"{h_head:.3f}")
    c3.metric("L_cil [m]", f"{L_cyl:.3f}")
    c4.metric("L_total [m]", f"{L_total:.3f}")

    c1.metric("V_cap (1) [m³]", f"{V_head:.3f}")
    c2.metric("V_total calculat [m³]", f"{V_total_calc:.3f}")
    c3.metric("ΔV = V_calc - V_țintă [m³]", f"{dV:.3f}")
    c4.metric("L/D rezultat [-]", f"{L_over_D_calc:.2f}")

    if warn_D:
        st.error(f"Depășește D_max: D = {D:.2f} m > D_max = {D_max:.2f} m")
    if warn_L:
        st.error(f"Depășește L_max: L_total = {L_total:.2f} m > L_max = {L_max:.2f} m")

# -------- Nivel–Volum --------
with tab_lv:
    st.subheader("Curba NIVEL–VOLUM (cilindru + capace ca termen constant)")
    h_vals = np.linspace(0.0, D, n_points)
    A_vals = np.array([level_segment_area(R, h) for h in h_vals])
    V_cyl_h = A_vals * L_cyl
    V_total_h = V_cyl_h + 2.0 * V_head
    df_lv = pd.DataFrame({"h [m]": h_vals, "Volum_cil [m³]": V_cyl_h, "Volum_total [m³]": V_total_h})
    st.dataframe(df_lv.head(12))

    fig, ax = plt.subplots()
    ax.plot(df_lv["h [m]"], df_lv["Volum_total [m³]"])
    ax.set_xlabel("Înălțime lichid h [m]")
    ax.set_ylabel("Volum total [m³]")
    ax.set_title("Curba NIVEL–VOLUM (orizontal)")
    st.pyplot(fig)

# -------- Verificare mecanică --------
with tab_mech:
    st.subheader("Verificare simplificată – efort cerc hidrostatic (rezervor atmosferic)")
    sigma_used = sigma_allow / SF
    h_design = D  # coloană reprezentativă
    t_req_mm = (rho * 9.80665 * h_design * R) / (sigma_used * 1000.0)
    t_disp_mm = t_nom - CA
    need = max(t_req_mm, t_min)
    ok = t_disp_mm >= need

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("σ utilizată [MPa]", f"{sigma_used:.2f}")
    c2.metric("t_req [mm]", f"{t_req_mm:.2f}")
    c3.metric("t_disp = t_nom - CA [mm]", f"{t_disp_mm:.2f}")
    c4.metric("Necesar ≥ max(t_req, t_min)", f"{need:.2f}")

    if ok:
        st.success("OK – grosimea este suficientă")
    else:
        st.error("Crește grosimea – t_disp < max(t_req, t_min)")

# -------- Saddle-uri --------
with tab_sad:
    st.subheader("Saddle-uri (simplificat)")
    S_rec_low = 0.4 * L_cyl
    S_rec_high = 0.5 * L_cyl
    span = L_total - 2.0 * a

    S_chosen = S_user if S_user > 0 else S_rec_low
    c1, c2, c3 = st.columns(3)
    c1.metric("Interval recomandat S [m]", f"{S_rec_low:.3f} – {S_rec_high:.3f}")
    c2.metric("Deschidere totală L_total - 2a [m]", f"{span:.3f}")
    c3.metric("S ales [m]", f"{S_chosen:.3f}")

    if S_chosen <= span:
        st.info("Check: S ≤ deschidere → OK")
    else:
        st.error("Check: S > deschidere → Ajustează distanța / offsetul a")

# =========================== Export Word (DOCX) – Concluzii ===========================
geom_dict = {
    "R [m]": R, "h_cap [m]": h_head, "L_cil [m]": L_cyl, "L_total [m]": L_total,
    "V_head (1) [m³]": V_head, "V_total calc [m³]": V_total_calc,
    "ΔV [m³]": dV, "L/D rezultat [-]": L_over_D
}
mech_dict = {
    "σ utilizată [MPa]": sigma_allow / SF, "h design [m]": D,
    "t_req [mm]": (rho * 9.80665 * D * R) / ((sigma_allow / SF) * 1000.0),
    "t_min [mm]": t_min, "CA [mm]": CA, "t_nom [mm]": t_nom, "t_disp [mm]": t_nom - CA
}
saddles_dict = {"S_rec_min [m]": 0.4 * L_cyl, "S_rec_max [m]": 0.5 * L_cyl, "Deschidere [m]": L_total - 2.0 * a}

docx_bytes = make_conclusions_docx(geom_dict, mech_dict, saddles_dict)
st.download_button("Descarcă raport (Word)", data=docx_bytes,
                   file_name="Raport_rezervor_orizontal.docx",
                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

st.caption("Notă: curba nivel–volum tratează volumul capetelor ca termen constant; pentru precizie ridicată la niveluri extreme, e necesară integrarea volumului capetelor.")
