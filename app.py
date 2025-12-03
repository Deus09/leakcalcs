# --- DÜZELTME BURADA YAPILDI: redirect ve url_for eklendi ---
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import os
from dotenv import load_dotenv
from translations import TRANSLATIONS
from utils import (
    convert_to_kelvin, convert_to_pa_direct, get_gas_properties,
    STD_P_REF, R_GAS, STD_T_K
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_dev_key')

# --- AYARLAR ---
LEMON_API_KEY = os.getenv('LEMON_API_KEY')
GA_ID = os.getenv('GA_ID', 'G-XXXXXXXXXX')

@app.context_processor
def inject_ga_id():
    return dict(ga_id=GA_ID)

@app.context_processor
def inject_is_pro():
    return dict(is_pro=session.get('is_pro', False))

# --- ÇEVİRİ SÖZLÜĞÜ ---

# --- LİSANS DOĞRULAMA ---
@app.route('/activate-license', methods=['POST'])
def activate_license():
    data = request.json
    license_key = data.get('license_key')
    if not license_key: return jsonify({'success': False, 'message': 'No key provided'})

    url = "https://api.lemonsqueezy.com/v1/licenses/activate"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {LEMON_API_KEY}"}
    payload = {"license_key": license_key, "instance_name": "LeakCalcs Web App"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        resp_data = response.json()
        if response.status_code == 200 and resp_data.get('activated'):
            session['is_pro'] = True 
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': resp_data.get('error', 'Invalid Key')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# --- SIFIRLAMA ROTASI ---
@app.route('/reset')
def reset_session():
    session.clear()
    return redirect(url_for('index'))

# --- SAYFA ROTALARI ---
@app.route('/pricing')
def pricing():
    lang_code = request.args.get('lang', 'en')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    return render_template('pricing.html', t=t, lang=lang_code)

@app.route('/', methods=['GET', 'POST'])
def index():
    lang_code = request.args.get('lang', 'en')
    if lang_code not in TRANSLATIONS: lang_code = 'en'
    t = TRANSLATIONS[lang_code]
    
    is_pro = session.get('is_pro', False)
    result = None
    error = None
    
    inputs = {
        'fluid': 'R134a', 'leak_amount': '0.5', 
        'op_pressure': '1.01325', 'op_pressure_unit': 'bar', 'op_temp': '25', 'op_temp_unit': 'C', 
        'he_pressure': '1.01325', 'he_pressure_unit': 'bar', 'he_temp': '25', 'he_temp_unit': 'C', 
        'he_purity': '100', 'calc_mode': 'oda', 'input_method': 'manual',
        'sys_charge': '150', 'lifespan': '10', 'max_loss': '10'
    }

    if request.method == 'POST':
        inputs.update(request.form)
        calc_mode = inputs.get('calc_mode', 'oda')
        fluid = inputs.get('fluid', 'R134a')
        input_method = inputs.get('input_method', 'manual')
        
        # PRO KONTROLÜ
        if fluid != 'R134a' and not is_pro:
            error = t['err_pro_required']
            inputs['fluid'] = 'R134a' 
            return render_template('index.html', result=None, error=error, inputs=inputs, t=t, lang=lang_code, is_pro=is_pro)

        try:
            # Ömür Hesabı
            calculated_leak_val = None
            if input_method == 'lifetime':
                if not all([inputs['sys_charge'], inputs['lifespan'], inputs['max_loss']]): raise ValueError(t['err_fill'])
                sys_charge = float(inputs['sys_charge'])
                lifespan = float(inputs['lifespan'])
                max_loss_pct = float(inputs['max_loss'])
                leak_mass_yr = (sys_charge * (max_loss_pct / 100.0)) / lifespan
                inputs['leak_amount'] = f"{leak_mass_yr:.4f}"
                calculated_leak_val = leak_mass_yr
            else:
                if not inputs['leak_amount']: raise ValueError(t['err_fill'])
                leak_mass_yr = float(inputs['leak_amount'])

            # Standart Hesaplamalar
            op_press_val = float(inputs['op_pressure'])
            op_temp_val = float(inputs['op_temp'])
            he_press_val = float(inputs['he_pressure'])
            he_temp_val = float(inputs['he_temp'])
            he_purity = float(inputs['he_purity']) / 100.0

            op_T_K = convert_to_kelvin(op_temp_val, inputs['op_temp_unit'])
            op_P_Pa = convert_to_pa_direct(op_press_val, inputs['op_pressure_unit'])
            he_T_K = convert_to_kelvin(he_temp_val, inputs['he_temp_unit'])
            he_P_Pa = convert_to_pa_direct(he_press_val, inputs['he_pressure_unit'])

            mw_gas, _, source_gas = get_gas_properties(fluid, STD_T_K, STD_P_REF)
            if mw_gas is None: raise ValueError(f"{fluid} {t['err_not_found']}")
            
            mol_per_sec = leak_mass_yr / (mw_gas * 31536000)
            correction = 0.975 if fluid == "R600a" else 0.985
            
            result_details = {
                "visc_gas_std": "N/A", "visc_he_std": "N/A", "visc_gas_op": "N/A", "visc_he_test": "N/A",
                "k_visc_std": "N/A", "k_visc": "N/A", "k_press": "N/A", "correction": f"{correction:.3f}",
                "calculated_from_lifetime": calculated_leak_val
            }

            if calc_mode == 'oda':
                q_std_raw = (mol_per_sec * R_GAS * STD_T_K) * 10
                q_std_corrected = q_std_raw * correction
                _, visc_gas_std, _ = get_gas_properties(fluid, STD_T_K, STD_P_REF)
                _, visc_he_std, _ = get_gas_properties("Helium", STD_T_K, STD_P_REF)
                
                if visc_gas_std and visc_he_std:
                    k_visc_std = visc_gas_std / visc_he_std
                    q_he_std = q_std_corrected * k_visc_std
                    _, visc_gas_op, _ = get_gas_properties(fluid, op_T_K, op_P_Pa)
                    q_op_final = q_std_corrected * (visc_gas_std / visc_gas_op) * (op_P_Pa**2 / STD_P_REF**2) if visc_gas_op else 0
                    _, visc_he_test, _ = get_gas_properties("Helium", he_T_K, he_P_Pa)
                    q_he_test_final = q_he_std * (visc_he_std / visc_he_test) * (he_P_Pa**2 / STD_P_REF**2) * he_purity if visc_he_test else 0
                    result_details.update({"visc_gas_std": f"{visc_gas_std:.2f}", "visc_he_std": f"{visc_he_std:.2f}", "visc_gas_op": f"{visc_gas_op:.2f}", "visc_he_test": f"{visc_he_test:.2f}", "k_visc_std": f"{k_visc_std:.3f}"})
                    result = {'mode': 'oda', "fluid": fluid, "q_std": f"{q_std_corrected:.2e}", "q_he_std": f"{q_he_std:.2e}", "q_op": f"{q_op_final:.2e}", "q_he_test": f"{q_he_test_final:.2e}", "units": { "op_p": f"{op_press_val} {inputs['op_pressure_unit']}", "op_t": f"{op_temp_val} °{inputs['op_temp_unit']}", "he_p": f"{he_press_val} {inputs['he_pressure_unit']}", "he_t": f"{he_temp_val} °{inputs['he_temp_unit']}" }, "details": result_details}
                else: raise ValueError("Viscosity failed")
            else:
                q_work_raw = (mol_per_sec * R_GAS * op_T_K) * 10
                q_work_corrected = q_work_raw * correction
                _, visc_gas_work, _ = get_gas_properties(fluid, op_T_K, op_P_Pa)
                _, visc_he_test, _ = get_gas_properties("Helium", he_T_K, he_P_Pa)
                if visc_gas_work and visc_he_test:
                    k_visc = visc_gas_work / visc_he_test
                    k_press = (he_P_Pa**2) / (op_P_Pa**2)
                    q_he_test_final = q_work_corrected * k_visc * k_press * he_purity
                    result_details.update({"visc_gas_work": f"{visc_gas_work:.2f}", "visc_he_test": f"{visc_he_test:.2f}", "k_visc": f"{k_visc:.3f}", "k_press": f"{k_press:.3f}"})
                    result = {'mode': 'musteri', "fluid": fluid, "q_work": f"{q_work_corrected:.2e}", "q_he_test": f"{q_he_test_final:.2e}", "units": { "op_p": f"{op_press_val} {inputs['op_pressure_unit']}", "op_t": f"{op_temp_val} °{inputs['op_temp_unit']}", "he_p": f"{he_press_val} {inputs['he_pressure_unit']}", "he_t": f"{he_temp_val} °{inputs['he_temp_unit']}" }, "details": result_details}
                else: raise ValueError("Viscosity failed")

        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template('index.html', result=result, error=error, inputs=inputs, t=t, lang=lang_code, is_pro=is_pro)

# --- YENİ SAYFALAR ---
@app.route('/about')
def about():
    lang_code = request.args.get('lang', 'en')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    return render_template('about.html', t=t, lang=lang_code)

@app.route('/blog/why-leak-rate-matters')
def blog_leak():
    lang_code = request.args.get('lang', 'en')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    return render_template('blog_leak.html', t=t, lang=lang_code)

@app.route('/blog/what-is-gwp')
def blog_gwp():
    lang_code = request.args.get('lang', 'en')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    return render_template('blog_gwp.html', t=t, lang=lang_code)

@app.route('/examples')
def examples():
    lang_code = request.args.get('lang', 'en')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    return render_template('example-data.html', t=t, lang=lang_code)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)