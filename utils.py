import CoolProp.CoolProp as CP

# Varsayılan değerler
STD_P_REF = 101325
R_GAS = 8.314
STD_T_K = 298.15
GAS_DB = {
    "CO2": {'mw': 44.01}, "Helium": {'mw': 4.0006}, "R-12": {'mw': 120.93},
    "R-123": {'mw': 152.93}, "R-1234yf": {'mw': 114.0}, "R-134a": {'mw': 102.03},
    "R-22": {'mw': 86.48}, "R-404A": {'mw': 97.6}, "R-407C": {'mw': 86.2},
    "R-410A": {'mw': 72.6}, "R-507": {'mw': 98.9}, "R-508B": {'mw': 95.39},
    "R-600a": {'mw': 58.00}, "SF6": {'mw': 146.054}, "R290": {'mw': 44.10}
}

# --- YARDIMCI FONKSİYONLAR ---
def convert_to_kelvin(value, unit):
    return (value - 32) * (5/9) + 273.15 if unit == 'F' else value + 273.15

def convert_to_pa_direct(value, unit):
    if unit == 'psig': return (value * 6894.76)
    elif unit == 'bar': return (value * 100000)
    return value

def get_coolprop_fluid_name(user_fluid_name):
    if user_fluid_name == "R600a": return "IsoButane"
    if user_fluid_name == "R290": return "Propane"
    if user_fluid_name == "R507": return "R507A"
    return user_fluid_name

def get_gas_properties(fluid_name, T_kelvin, P_pascal_input):
    cp_name = get_coolprop_fluid_name(fluid_name)
    P_absolute_approx = P_pascal_input + 101325 
    try:
        visc_pa_s = CP.PropsSI('V', 'T', T_kelvin, 'P', P_absolute_approx, cp_name)
        visc_upa_s = visc_pa_s * 1e6
        mw_kg_mol = CP.PropsSI('MOLARMASS', cp_name)
        mw_g_mol = mw_kg_mol * 1000
        return mw_g_mol, visc_upa_s, "CoolProp"
    except:
        if fluid_name in GAS_DB: return GAS_DB[fluid_name]['mw'], None, "Tablo"
        return None, None, "Yok"
