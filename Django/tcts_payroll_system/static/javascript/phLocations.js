/**
 * Philippine Address Fields Handler
 * 
 * This script dynamically loads region, province, city, and barangay data
 * for Philippine addresses in web forms.
 * 
 * @param {Object} config - Configuration object with element IDs
 */
function initializeAddressFields(config) {
    // Get elements using the provided config
    const regionInput = document.getElementById(config.regionInputId);
    const provinceInput = document.getElementById(config.provinceInputId);
    const cityInput = document.getElementById(config.cityInputId);
    const barangayInput = document.getElementById(config.barangayInputId);
    
    const regionList = document.getElementById(config.regionListId);
    const provinceList = document.getElementById(config.provinceListId);
    const cityList = document.getElementById(config.cityListId);
    const barangayList = document.getElementById(config.barangayListId);

    // Base URL for AJAX calls (can be configured)
    const baseUrl = config.baseUrl || '/payroll_system/ajax';

    // Store current location codes
    let currentRegionCode = "";
    let currentProvinceCode = "";
    let currentCityCode = "";
    
    // Function to enable/disable fields based on their dependencies
    function updateFieldStates() {
        if (provinceInput) {
            provinceInput.disabled = !regionInput?.value;
        }
        if (cityInput) {
            cityInput.disabled = !provinceInput?.value;
        }
        if (barangayInput) {
            barangayInput.disabled = !cityInput?.value;
        }
    }

    // Function to fetch provinces for a region
    function fetchProvinces(regionCode) {
        if (!regionCode) return;
        
        fetch(`${baseUrl}/get-provinces/?region=${regionCode}`)
            .then(response => response.json())
            .then(data => {
                if (provinceList) {
                    provinceList.innerHTML = "";
                    data.provinces.forEach(p => {
                        const option = document.createElement("option");
                        option.value = p.provDesc;
                        option.setAttribute("data-code", p.provCode);
                        provinceList.appendChild(option);
                    });
                    
                    // If province has a value, trigger its input handler
                    if (provinceInput && provinceInput.value) {
                        const event = new Event('input');
                        provinceInput.dispatchEvent(event);
                    }
                }
            })
            .catch(error => console.error("Error fetching provinces:", error));
    }

    // Function to fetch cities for a province
    function fetchCities(provinceCode) {
        if (!provinceCode) return;
        
        fetch(`${baseUrl}/get-cities/?province=${provinceCode}`)
            .then(response => response.json())
            .then(data => {
                if (cityList) {
                    cityList.innerHTML = "";
                    data.cities.forEach(c => {
                        const option = document.createElement("option");
                        option.value = c.citymunDesc;
                        option.setAttribute("data-code", c.citymunCode);
                        cityList.appendChild(option);
                    });
                    
                    // If city has a value, trigger its input handler
                    if (cityInput && cityInput.value) {
                        const event = new Event('input');
                        cityInput.dispatchEvent(event);
                    }
                }
            })
            .catch(error => console.error("Error fetching cities:", error));
    }

    // Function to fetch barangays for a city
    function fetchBarangays(cityCode) {
        if (!cityCode) return;
        
        fetch(`${baseUrl}/get-barangays/?city=${cityCode}`)
            .then(response => response.json())
            .then(data => {
                if (barangayList) {
                    barangayList.innerHTML = "";
                    data.barangays.forEach(b => {
                        const option = document.createElement("option");
                        option.value = b.brgyDesc;
                        option.setAttribute("data-code", b.brgyCode);
                        barangayList.appendChild(option);
                    });
                }
            })
            .catch(error => console.error("Error fetching barangays:", error));
    }

    // Setup event listeners if elements exist
    if (regionInput) {
        regionInput.addEventListener("change", function() {
            if (!this.value) {
                if (provinceInput) provinceInput.value = "";
                if (cityInput) cityInput.value = "";
                if (barangayInput) barangayInput.value = "";
            }
            updateFieldStates();
        });
        
        regionInput.addEventListener("input", function() {
            const selectedOption = document.querySelector(`#${config.regionListId} option[value="${regionInput.value}"]`);
            if (selectedOption) {
                currentRegionCode = selectedOption.dataset.code;
                if (provinceInput) provinceInput.value = "";
                if (cityInput) cityInput.value = "";
                if (barangayInput) barangayInput.value = "";
                
                fetchProvinces(currentRegionCode);
            }
        });
        
        // If region already has a value on page load, fetch provinces
        if (regionInput.value) {
            const selectedOption = document.querySelector(`#${config.regionListId} option[value="${regionInput.value}"]`);
            if (selectedOption) {
                currentRegionCode = selectedOption.dataset.code;
                fetchProvinces(currentRegionCode);
            }
        }
    }
    
    if (provinceInput) {
        provinceInput.addEventListener("change", function() {
            if (!this.value) {
                if (cityInput) cityInput.value = "";
                if (barangayInput) barangayInput.value = "";
            }
            updateFieldStates();
        });
        
        provinceInput.addEventListener("input", function() {
            const selectedOption = document.querySelector(`#${config.provinceListId} option[value="${provinceInput.value}"]`);
            if (selectedOption) {
                currentProvinceCode = selectedOption.dataset.code;
                if (cityInput) cityInput.value = "";
                if (barangayInput) barangayInput.value = "";
                
                fetchCities(currentProvinceCode);
            }
        });
        
        // If province already has a value on page load, fetch cities
        if (provinceInput.value) {
            const selectedOption = document.querySelector(`#${config.provinceListId} option[value="${provinceInput.value}"]`);
            if (selectedOption) {
                currentProvinceCode = selectedOption.dataset.code;
                fetchCities(currentProvinceCode);
            }
        }
    }
    
    if (cityInput) {
        cityInput.addEventListener("change", function() {
            if (!this.value) {
                if (barangayInput) barangayInput.value = "";
            }
            updateFieldStates();
        });
        
        cityInput.addEventListener("input", function() {
            const selectedOption = document.querySelector(`#${config.cityListId} option[value="${cityInput.value}"]`);
            if (selectedOption) {
                currentCityCode = selectedOption.dataset.code;
                if (barangayInput) barangayInput.value = "";
                
                fetchBarangays(currentCityCode);
            }
        });
        
        // If city already has a value on page load, fetch barangays
        if (cityInput.value) {
            const selectedOption = document.querySelector(`#${config.cityListId} option[value="${cityInput.value}"]`);
            if (selectedOption) {
                currentCityCode = selectedOption.dataset.code;
                fetchBarangays(currentCityCode);
            }
        }
    }
    
    // Initialize field states based on current values
    updateFieldStates();
}