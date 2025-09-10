import math
import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from openpyxl import Workbook

st.set_page_config(page_title="Rezervor orizontal - dimensionare", layout="wide")

# === Funcții ===
def head_volume_21_ellipsoidal(R):
    # V_head = (1/3) * pi * R^3
    return (math.pi / 3.0) * (R ** 3)

def level_segment_area(R, h):
    # A(h) = R^2*acos((R-h)/R) - (R-h)*sqrt(2Rh - h^2), pentru 0<=h<=2R
    if h <= 0:
        return 0.0
    if h >= 2*R:
        return math.pi * R**2
    return R**2 * math.acos((R - h) / R) - (R - h) * math.sqrt(max(0.0, 2*R*h - h**2))

st.title("Dimensionare Rezervor Orizontal")

with st.sidebar:
    st.header("Date de intrare")
    rho = st.number_input("Densitate lichid, ρ [kg/m³]", value=1000.0, min_value=1.0)
    V_work = st.number_input("Volum util necesar V_util [m³]", value=100.0, min_value=0.0)
    f_fill = st.slider("Fracție de umplere admisă f_umplere [-]", 0.5, 1.0, 0.9, 0.01)
    V_total_target = V_work / f_fill if f_fill>0 else 0.0
    st.caption(f"Volum total de proiectare V_total = {V_total_target:.3f} m³")
    L_over_D = st.slider("Raport L/D (recomandat 2–5)", 1.50, 6.00, 3.00, step=0.01, format="%.2f")
    D = st.number_input("Diametru ales D [m]", value=3.2, min_value=0.1)
    CA = st.number_input("Adaos coroziune CA [mm]", value=1.0, min_value=0.0)
    sigma_allow = st.number_input("Tensiune admisă material σ_adm [MPa]", value=120.0, min_value=1.0)
    SF = st.number_input("Factor de siguranță SF [-]", value=1.5, min_value=1.0)
    t_min = st.number_input("Grosime minimă fabricație t_min [mm]", value=6.0, min_value=0.0, step=0.5)
    t_nom = st.number_input("Grosime nominală aleasă t_nom [mm]", value=8.0, min_value=0.0, step=0.5)
    a = st.number_input("Distanță de la tangentă la centrul saddle a [m]", value=0.2, min_value=0.0, step=0.05)

# === Geometrie ===
R = D/2.0
h_head = D/4.0                      # 2:1 elipsoidal
L_total = L_over_D * D
L_cyl = max(0.0, L_total - 2.0*h_head)
V_head = head_volume_21_ellipsoidal(R)
V_cyl = math.pi * R**2 * L_cyl
V_total_guess = V_cyl + 2.0*V_head
dV = V_total_guess - V_total_target

tab_geom, tab_lv, tab_mech, tab_sad, tab_sketch = st.tabs(
    ["Geometrie", "Nivel–Volum", "Verificare mecanică", "Saddle-uri", "Schiță"]
)

with tab_geom:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rază R [m]", f"{R:.3f}")
    c2.metric("Adâncime capac h_cap [m]", f"{h_head:.3f}")
    c3.metric("Lungime cilindru L_cil [m]", f"{L_cyl:.3f}")
    c4.metric("Lungime totală L_total [m]", f"{L_total:.3f}")
    c1.metric("V_cap (1) [m³]", f"{V_head:.3f}")
    c2.metric("V_cil [m³]", f"{V_cyl:.3f}")
    c3.metric("V_total calculat [m³]", f"{V_total_guess:.3f}")
    c4.metric("ΔV = V_calc - V_țintă [m³]", f"{dV:.3f}")

    st.info("Ajustează D și/sau L/D astfel încât ΔV ≈ 0 și L_cil ≥ 0.")

with tab_lv:
    st.write("**Curba nivel–volum** (aprox.: volumul capetelor se adaugă ca termen constant)")
    n = st.slider("Număr puncte pe înălțime", 20, 200, 100, 5)
    import numpy as np
    h_vals = np.linspace(0.0, D, n)
    A_vals = np.array([level_segment_area(R, h) for h in h_vals])
    V_cyl_h = A_vals * L_cyl
    V_total_h = V_cyl_h + 2.0*V_head
    import pandas as pd
    df = pd.DataFrame({"h [m]": h_vals, "Volum_cil [m³]": V_cyl_h, "Volum_total [m³]": V_total_h})
    st.dataframe(df.head(10))
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(df["h [m]"], df["Volum_total [m³]"])
    ax.set_xlabel("Înălțime lichid h [m]")
    ax.set_ylabel("Volum total [m³]")
    ax.set_title("Curba NIVEL–VOLUM (orizontal)")
    st.pyplot(fig)

with tab_mech:
    st.write("**Verificare simplificată – efort cerc hidrostatic (rezervor atmosferic)**")
    sigma_used = sigma_allow / SF
    h_design = D   # înălțime reprezentativă a coloanei de lichid
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

with tab_sad:
    st.write("**Saddle-uri (simplificat)**")
    S_rec_low = 0.4 * L_cyl
    S_rec_high = 0.5 * L_cyl
    S_chosen = st.number_input("Alege S (distanța centru–centru între saddle-uri) [m]", value=round(S_rec_low,3), min_value=0.0)
    span = L_total - 2.0*a
    c1, c2, c3 = st.columns(3)
    c1.metric("Interval recomandat S", f"{S_rec_low:.3f} – {S_rec_high:.3f} m")
    c2.metric("Deschidere totală disponibilă", f"{span:.3f} m")
    c3.metric("Check S ≤ deschidere", "OK" if S_chosen <= span else "Depășește")

with tab_sketch:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Ellipse

    st.subheader("Schiță rezervor orizontal – capace elipsoidale 2:1 (la scară)")

    # ---------------- Helperi pentru linii de cotă (text deasupra) ----------------
    def cota_oriz(ax, x1, x2, y, label, dy_text=0.08, color="black"):
        ax.annotate(
            "", xy=(x1, y), xytext=(x2, y),
            arrowprops=dict(arrowstyle="<->", lw=1.4, color=color, shrinkA=4, shrinkB=4)
        )
        ax.text(
            (x1 + x2) / 2, y + dy_text * D, label,
            ha="center", va="bottom", fontsize=11, color=color,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5)
        )

    def cota_vert(ax, x, y1, y2, label, dx_text=0.06, color="black"):
        ax.annotate(
            "", xy=(x, y1), xytext=(x, y2),
            arrowprops=dict(arrowstyle="<->", lw=1.4, color=color, shrinkA=4, shrinkB=4)
        )
        ax.text(
            x + dx_text * D, (y1 + y2) / 2, label,
            ha="left", va="center", rotation=90, fontsize=11, color=color,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5)
        )

    # ---------------- Geometrie pentru desen ----------------
    Rplot   = R
    Dplot   = D
    Lc      = L_cyl
    hcap    = h_head                  # = D/4 pentru 2:1
    Ltot    = L_total
    x_tan_L = hcap                    # poziția liniei tangente stânga
    x_tan_R = hcap + Lc               # poziția liniei tangente dreapta

    # Poziții saddle-uri (centru–centru)
    x_s1 = x_tan_L - a                # centrul saddle 1
    x_s2 = x_tan_L + S_chosen         # centrul saddle 2
    span_av = Ltot - 2 * a            # deschiderea disponibilă

    # ---------------- Desen ----------------
    fig, ax = plt.subplots(figsize=(11, 3.6))

    # Cilindru
    ax.add_patch(Rectangle((x_tan_L, -Rplot), Lc, 2 * Rplot, fill=False, lw=2.5, joinstyle="round"))

    # Capace elipsoidale 2:1 – jumătăți de elipsă (la scară)
    eL = Ellipse((x_tan_L, 0), width=2 * hcap, height=2 * Rplot, angle=0, fill=False, lw=2.5)
    eR = Ellipse((x_tan_R, 0), width=2 * hcap, height=2 * Rplot, angle=0, fill=False, lw=2.5)
    ax.add_patch(eL)
    ax.add_patch(eR)

    # Linii tangente (cap–cilindru)
    ax.plot([x_tan_L, x_tan_L], [-Rplot, Rplot], color="black", lw=2.5)
    ax.plot([x_tan_R, x_tan_R], [-Rplot, Rplot], color="black", lw=2.5)

    # Axa rezervorului (ghid punctat)
    ax.axhline(0, color="0.5", lw=0.8, ls="--", alpha=0.5)

    # Saddle-uri: patine colorate
    pad_h = 0.15 * Rplot
    ax.add_patch(Rectangle((x_s1 - 0.05 * Dplot, -Rplot - pad_h), 0.10 * Dplot, pad_h, color="#ff8c00"))
    ax.add_patch(Rectangle((x_s2 - 0.05 * Dplot, -Rplot - pad_h), 0.10 * Dplot, pad_h, color="#2e7d32"))
    ax.text(x_s1, -Rplot - pad_h - 0.22 * Dplot, "Saddle 1", ha="center", va="top", fontsize=10)
    ax.text(x_s2, -Rplot - pad_h - 0.22 * Dplot, "Saddle 2", ha="center", va="top", fontsize=10)

    # ---------------- Cote (text deasupra liniilor) ----------------
    # Diametru D (vertical, la mijlocul cilindrului)
    cota_vert(ax, x_tan_L + Lc / 2, -Rplot, Rplot, f"D = {D:.2f} m")

    # L_cil (sus)
    cota_oriz(ax, x_tan_L, x_tan_R, 1.28 * Rplot, f"L_cil = {Lc:.2f} m", dy_text=0.06)

    # L_total (jos)
    cota_oriz(ax, 0, Ltot, -1.45 * Rplot, f"L_total = {Ltot:.2f} m", dy_text=0.06)

    # a (offset de la tangentă la centrul saddle 1)
    cota_oriz(ax, x_s1, x_tan_L, -1.05 * Rplot, f"a = {a:.2f} m", dy_text=0.06)

    # S ales (albastru)
    cota_oriz(ax, x_s1, x_s2, -1.25 * Rplot, f"S ales = {S_chosen:.2f} m", dy_text=0.06, color="tab:blue")

    # Deschidere disponibilă (verde)
    cota_oriz(ax, x_tan_L - a, x_tan_R + a, -1.65 * Rplot, f"Deschidere = {span_av:.2f} m", dy_text=0.06, color="tab:green")

    # Aspect grafic
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.35 * Dplot, Ltot + 0.35 * Dplot)
    ax.set_ylim(-2.0 * Rplot, 1.75 * Rplot)
    ax.axis("off")

    st.pyplot(fig)

    # Export PNG
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    st.download_button("Descarcă schița (PNG)", data=buf, file_name="schita_rezervor_orizontal.png", mime="image/png")

