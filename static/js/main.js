document.addEventListener('DOMContentLoaded', function() {
    const modeSelect = document.getElementById('calcModeSelect');
    const inputMethodSelect = document.getElementById('inputMethodSelect');
    const fluidSelect = document.getElementById('fluidSelect');
    const hiddenCalcMode = document.getElementById('hiddenCalcMode');
    const hiddenInputMethod = document.getElementById('hiddenInputMethod');
    const form = document.getElementById('calcForm');
    const leakInput = document.getElementById('leakInput');
    const lifetimeBox = document.getElementById('lifetimeBox');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const proUpsellModal = new bootstrap.Modal(document.getElementById('proUpsellModal'));
    
    // Get config from window object
    const config = window.LEAK_CALCS_CONFIG || {};
    const isPro = config.isPro;
    const placeholderRoom = config.placeholders.room;
    const placeholderCust = config.placeholders.cust;

    function checkAndTriggerUpsell(element, allowedValue, resetValue) {
        if (!isPro && element.value !== allowedValue) {
            proUpsellModal.show();
            element.value = resetValue;
            updateUI();
            return true;
        }
        return false;
    }

    function updateUI() {
        const isOda = modeSelect.value === 'oda';
        const isLifetime = inputMethodSelect.value === 'lifetime';
        const selectedFluid = fluidSelect.value;
        const isFluidR134a = (selectedFluid === 'R134a');
        const isUnlocked = isPro || isFluidR134a;

        hiddenCalcMode.value = modeSelect.value;
        hiddenInputMethod.value = inputMethodSelect.value;

        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (['leak_amount', 'fluid', 'calcModeSelect', 'hiddenCalcMode', 'he_purity', 'inputMethodSelect', 'hiddenInputMethod', 'sys_charge', 'lifespan', 'max_loss'].includes(input.name) || input.id === 'calcModeSelect' || input.id === 'fluidSelect' || input.id === 'inputMethodSelect') return;
            input.disabled = isOda;
        });

        if (isOda) {
            document.getElementsByName('op_pressure')[0].value = '1.01325'; document.getElementsByName('op_pressure_unit')[0].value = 'bar';
            document.getElementsByName('op_temp')[0].value = '25'; document.getElementsByName('op_temp_unit')[0].value = 'C';
            document.getElementsByName('he_pressure')[0].value = '1.01325'; document.getElementsByName('he_pressure_unit')[0].value = 'bar';
            document.getElementsByName('he_temp')[0].value = '25'; document.getElementsByName('he_temp_unit')[0].value = 'C';
            document.getElementsByName('he_purity')[0].value = '100';
            leakInput.placeholder = placeholderRoom;
        } else {
            leakInput.placeholder = placeholderCust;
        }

        if (isLifetime && isUnlocked) {
            lifetimeBox.style.display = 'block';
            leakInput.disabled = true;
            leakInput.value = '';
            leakInput.placeholder = "Auto Calculated";
        } else {
            lifetimeBox.style.display = 'none';
            leakInput.disabled = false;
        }
    }

    modeSelect.addEventListener('change', function() { if(!checkAndTriggerUpsell(this, 'oda', 'oda')) updateUI(); });
    inputMethodSelect.addEventListener('change', function() { if(!checkAndTriggerUpsell(this, 'manual', 'manual')) updateUI(); });
    fluidSelect.addEventListener('change', function() {
        if (!isPro && this.value !== 'R134a') {
            proUpsellModal.show();
            this.value = 'R134a';
            updateUI();
        } else { updateUI(); }
    });

    updateUI();

    form.addEventListener('submit', function(e) {
        if (!form.checkValidity()) return;
        e.preventDefault();
        loadingOverlay.style.display = 'flex';
        const messages = ["Analysing Input Parameters...", "Calculating Gas Viscosity...", "Applying ASTM E499 Standards...", "Converting Units...", "Finalizing Report..."];
        let i = 0;
        loadingText.innerText = messages[0];
        const interval = setInterval(() => {
            i++;
            if (i < messages.length) loadingText.innerText = messages[i];
        }, 500); 
        setTimeout(() => { clearInterval(interval); form.submit(); }, 2500);
    });
});

function activateLicense() {
    const key = document.getElementById('licenseKeyInput').value;
    const msgDiv = document.getElementById('licenseMsg');
    if (!key) { msgDiv.innerText = "Please enter a key."; return; }
    msgDiv.innerText = "Verifying...";
    msgDiv.className = "small text-info";
    fetch('/activate-license', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({license_key: key})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            msgDiv.innerText = "Success! Reloading...";
            msgDiv.className = "small text-success";
            setTimeout(() => location.reload(), 1000);
        } else {
            msgDiv.innerText = "Error: " + data.message;
            msgDiv.className = "small text-danger";
        }
    })
    .catch(error => { msgDiv.innerText = "Network Error."; msgDiv.className = "small text-danger"; });
}
