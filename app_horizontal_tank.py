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

st.title("Dimensionare rezervor orizontal (cilindru + capace elipsoidale 2:1)")

with st.sidebar:
    st.header("Date de intrare")
    rho = st.number_input("Densitate lichid, ρ [kg/m³]", value=1000.0, min_value=1.0)
    V_work = st.number_input("Volum util necesar V_util [m³]", value=100.0, min_value=0.0)
    f_fill = st.slider("Fracție de umplere admisă f_umplere [-]", 0.5, 1.0, 0.9, 0.01)
    V_total_target = V_work / f_fill if f_fill>0 else 0.0
    st.caption(f"Volum total de proiectare V_total = {V_total_target:.3f} m³")
    L_over_D = st.slider("Raport L/D (recomandat 2–5)", 1.5, 6.0, 3.0, 0.1)
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

tab_geom, tab_lv, tab_mech, tab_sad = st.tabs(["Geometrie", "Nivel–Volum", "Verificare mecanică", "Saddle-uri"])

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
    st.success("OK – grosimea este suficientă") if ok else st.error("Crește grosimea – t_disp < max(t_req, t_min)")

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

# Export Excel minimal
from openpyxl import Workbook
def to_excel_buffer(df, inputs_dict):
    wb = Workbook()
    ws = wb.active; ws.title="Date"
    r=1
    for k,v in inputs_dict.items():
        ws.cell(r,1).value=str(k); ws.cell(r,2).value=float(v) if isinstance(v,(int,float)) else v; r+=1
    ws2=wb.create_sheet("Nivel–Volum")
    ws2.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws2.append(list(row))
    buf=io.BytesIO(); wb.save(buf); buf.seek(0); return buf

inputs_dict = {"ρ [kg/m³]":rho,"V_util [m³]":V_work,"f_umplere [-]":f_fill,"V_total țintă [m³]":V_total_target,
               "L/D [-]":L_over_D,"D [m]":D,"R [m]":R,"L_cil [m]":L_cyl,"L_total [m]":L_total,
               "σ utilizată [MPa]":sigma_allow/SF,"t_req [mm]":(rho*9.80665*D*R)/((sigma_allow/SF)*1000.0),
               "t_min [mm]":t_min,"CA [mm]":CA,"t_nom [mm]":t_nom,"t_disp [mm]":t_nom-CA}
buf = to_excel_buffer(df, inputs_dict)
st.download_button("Descarcă Excel", data=buf, file_name="Rezervor_orizontal_Streamlit.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
