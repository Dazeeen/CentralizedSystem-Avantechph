(function () {
    function markFieldState(field) {
        if (!field || !field.closest) {
            return;
        }
        // Keep validation highlights scoped to the field wrapper, not the whole row.
        var container = field.closest('.mb-2, .mb-3, .mb-4, .mb-5, .form-group, .col, [class*="col-"]') || field.parentElement;
        if (!container || !container.classList) {
            return;
        }
        if (typeof field.checkValidity === 'function' && !field.checkValidity()) {
            container.classList.add('field-has-error');
        } else {
            container.classList.remove('field-has-error');
        }
    }

    function wireFormValidation(form) {
        if (!form || form.dataset.validationBound === '1') {
            return;
        }
        form.dataset.validationBound = '1';
        form.removeAttribute('novalidate');

        form.addEventListener('submit', function (event) {
            var submitter = event.submitter;
            if (submitter && (submitter.hasAttribute('formnovalidate') || submitter.dataset.skipValidation === '1')) {
                return;
            }

            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                form.classList.add('was-validated');
                form.querySelectorAll('input, select, textarea').forEach(markFieldState);
            }
        });

        form.querySelectorAll('input, select, textarea').forEach(function (field) {
            field.addEventListener('input', function () {
                markFieldState(field);
            });
            field.addEventListener('change', function () {
                markFieldState(field);
            });
        });
    }

    function wirePasswordToggle(input) {
        if (!input || input.dataset.passwordToggleBound === '1') {
            return;
        }
        input.dataset.passwordToggleBound = '1';

        var currentType = (input.getAttribute('type') || '').toLowerCase();
        if (currentType !== 'password') {
            return;
        }

        if (input.parentElement && input.parentElement.classList.contains('password-toggle-wrap')) {
            return;
        }

        var wrapper = document.createElement('div');
        wrapper.className = 'input-group password-toggle-wrap';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline-secondary password-toggle-btn';
        button.setAttribute('aria-label', 'Show password');
        button.setAttribute('aria-pressed', 'false');
        button.innerHTML = '<span class="password-toggle-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5A3.5 3.5 0 1 0 12 15.5Z" stroke="currentColor" stroke-width="1.8"/><path class="password-toggle-slash" d="M4 20L20 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></span>';

        button.addEventListener('click', function () {
            var isPassword = input.getAttribute('type') === 'password';
            input.setAttribute('type', isPassword ? 'text' : 'password');
            button.classList.toggle('is-visible', isPassword);
            button.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
            button.setAttribute('aria-pressed', isPassword ? 'true' : 'false');
        });

        wrapper.appendChild(button);
    }

    function refreshCaptcha(button) {
        var refreshUrl = button.dataset.captchaRefreshUrl;
        if (!refreshUrl || !window.fetch) {
            return;
        }

        var scope = button.closest('[data-captcha-scope="1"]') || button.closest('form') || document;
        var image = scope.querySelector('img.captcha') || scope.querySelector('img[alt="captcha"]');
        var hiddenKey = scope.querySelector('input[type="hidden"][name$="captcha_0"], input[type="hidden"][id$="captcha_0"]');
        var responseField = scope.querySelector('input[name$="captcha_1"], input[id$="captcha_1"]');

        button.disabled = true;

        fetch(refreshUrl, {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Failed to refresh captcha');
                }
                return response.json();
            })
            .then(function (data) {
                if (image && data && data.image_url) {
                    var separator = data.image_url.indexOf('?') === -1 ? '?' : '&';
                    image.setAttribute('src', data.image_url + separator + 'refresh=' + Date.now());
                }
                if (hiddenKey && data && data.key) {
                    hiddenKey.value = data.key;
                }
                if (responseField) {
                    responseField.value = '';
                    responseField.focus();
                }
            })
            .catch(function (error) {
                if (window.console && typeof window.console.warn === 'function') {
                    window.console.warn('Captcha refresh failed', error);
                }
            })
            .then(function () {
                button.disabled = false;
            });
    }

    function wireCaptchaRefresh(button) {
        if (!button) {
            return;
        }
        button.dataset.captchaRefreshBound = '1';
    }

    function extractCityFromAddressObject(addressObject) {
        if (!addressObject) {
            return '';
        }
        if (Array.isArray(addressObject)) {
            for (var i = 0; i < addressObject.length; i += 1) {
                var item = addressObject[i];
                if (!item || typeof item !== 'object') continue;
                var id = String(item.id || '');
                if (id.indexOf('place.') === 0) {
                    return String(item.text || item.name || '').trim();
                }
            }
            return '';
        }
        if (typeof addressObject === 'object') {
            return (
                addressObject.city
                || addressObject.town
                || addressObject.municipality
                || addressObject.village
                || addressObject.county
                || addressObject.state
                || ''
            );
        }
        return '';
    }

    function extractCityFromFeature(feature) {
        var properties = (feature && feature.properties && typeof feature.properties === 'object') ? feature.properties : {};
        return String(
            properties.city
            || properties.town
            || properties.municipality
            || properties.village
            || properties.county
            || properties.state
            || ''
        ).trim();
    }

    function buildFeatureLabel(feature) {
        if (!feature || typeof feature !== 'object') return '';
        var properties = (feature.properties && typeof feature.properties === 'object') ? feature.properties : {};
        return String(properties.display_name || properties.name || feature.name || properties.street || '').trim();
    }

    function findCompanionCityField(addressField) {
        var root = addressField.closest('form, .modal, .crm-profile-pane, .row, .col-12, .col-md-8, .col-md-6') || document;
        return root.querySelector('input[name="city"], textarea[name="city"], #infoCity, #editCity, #id_city');
    }

    function ensureDatalistForAddressField(field) {
        var listId = field.getAttribute('list');
        if (listId) {
            var existingList = document.getElementById(listId);
            if (existingList) {
                return existingList;
            }
        }
        listId = 'home-address-list-' + (field.id || Math.random().toString(36).slice(2, 10));
        var datalist = document.createElement('datalist');
        datalist.id = listId;
        field.setAttribute('list', listId);
        document.body.appendChild(datalist);
        return datalist;
    }

    function wireFreeAddressAutocompleteField(field) {
        if (!field || field.dataset.freeAddressAutocompleteBound === '1') {
            return;
        }
        if ((field.tagName || '').toLowerCase() !== 'input') {
            return;
        }

        field.dataset.freeAddressAutocompleteBound = '1';
        var datalist = ensureDatalistForAddressField(field);
        var suggestionMetaByAddress = {};
        var debounceTimer = null;
        var requestToken = 0;
        var abortController = null;
        var defaultAddressSuggestions = [
            'Quezon City, Metro Manila, Philippines',
            'Manila, Metro Manila, Philippines',
            'Makati, Metro Manila, Philippines',
            'Taguig, Metro Manila, Philippines',
            'Pasig, Metro Manila, Philippines',
            'Cebu City, Cebu, Philippines',
        ];

        function renderSimpleSuggestions(labels) {
            suggestionMetaByAddress = {};
            datalist.innerHTML = '';
            (labels || []).forEach(function (label) {
                var value = String(label || '').trim();
                if (!value) return;
                suggestionMetaByAddress[value] = { display_name: value, address: {} };
                var opt = document.createElement('option');
                opt.value = value;
                datalist.appendChild(opt);
            });
        }

        function ensureDefaultSuggestionsVisible() {
            if (!datalist.options || datalist.options.length === 0) {
                renderSimpleSuggestions(defaultAddressSuggestions);
            }
        }

        function applySelectedSuggestionCity() {
            var selected = suggestionMetaByAddress[field.value || ''];
            if (!selected) {
                return;
            }
            var tryApplyCity = function (candidate) {
                var cityValue = String(candidate || '').trim();
                if (!cityValue) return false;
                var cityField = findCompanionCityField(field);
                if (!cityField || cityField.readOnly || cityField.disabled) {
                    return false;
                }
                cityField.value = cityValue;
                cityField.dispatchEvent(new Event('input', { bubbles: true }));
                cityField.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            };

            var fallbackCity = String(selected.__derived_city || '').trim()
                || extractCityFromAddressObject(selected.context || selected.address || selected.properties || {});
            if (tryApplyCity(fallbackCity)) {
                return;
            }

            var properties = (selected && selected.properties && typeof selected.properties === 'object') ? selected.properties : {};
            var osmTypeRaw = String(properties.osm_type || '').toLowerCase();
            var osmId = String(properties.osm_id || '').trim();
            var osmPrefix = '';
            if (osmTypeRaw === 'node') osmPrefix = 'N';
            else if (osmTypeRaw === 'way') osmPrefix = 'W';
            else if (osmTypeRaw === 'relation') osmPrefix = 'R';
            if (!osmPrefix || !osmId) {
                return;
            }

            var lookupUrl = 'https://nominatim.openstreetmap.org/lookup?format=jsonv2&addressdetails=1&osm_ids=' + encodeURIComponent(osmPrefix + osmId);
            fetch(lookupUrl, { headers: { 'Accept': 'application/json' } })
                .then(function (response) {
                    if (!response.ok) throw new Error('Lookup failed');
                    return response.json();
                })
                .then(function (rows) {
                    var first = Array.isArray(rows) && rows.length ? rows[0] : null;
                    var addr = first && typeof first.address === 'object' ? first.address : {};
                    var cityValue = extractCityFromAddressObject(addr);
                    tryApplyCity(cityValue);
                })
                .catch(function () {
                    return;
                });
        }

        field.addEventListener('change', applySelectedSuggestionCity);
        field.addEventListener('blur', applySelectedSuggestionCity);

        function fetchSuggestionsForField(forceIfFocused) {
            var query = (field.value || '').trim();
            var countryCode = String(field.getAttribute('data-country-code') || 'ph').trim().toLowerCase() || 'ph';
            if (query.length < 2) {
                if (forceIfFocused) {
                    ensureDefaultSuggestionsVisible();
                } else {
                    ensureDefaultSuggestionsVisible();
                }
                return;
            }
            if (abortController) {
                abortController.abort();
            }
            abortController = new AbortController();
            requestToken += 1;
            var token = requestToken;
            var endpoint = 'https://nominatim.openstreetmap.org/search?format=geojson&addressdetails=1&countrycodes=' + encodeURIComponent(countryCode) + '&limit=6&q=' + encodeURIComponent(query);
            fetch(endpoint, {
                headers: {
                    'Accept': 'application/json',
                },
                signal: abortController.signal,
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Address lookup failed');
                    }
                    return response.json();
                })
                .then(function (payload) {
                    if (token !== requestToken) return;
                    if (forceIfFocused && document.activeElement !== field) return;
                    var rows = (payload && Array.isArray(payload.features)) ? payload.features : [];
                    suggestionMetaByAddress = {};
                    datalist.innerHTML = '';
                    rows.forEach(function (row) {
                        var label = buildFeatureLabel(row);
                        if (!label) return;
                        row.__derived_city = extractCityFromFeature(row);
                        suggestionMetaByAddress[label] = row;
                        var opt = document.createElement('option');
                        opt.value = label;
                        datalist.appendChild(opt);
                    });
                    if (!rows.length) {
                        ensureDefaultSuggestionsVisible();
                    }
                })
                .catch(function () {
                    ensureDefaultSuggestionsVisible();
                });
        }

        field.addEventListener('focus', function () {
            ensureDefaultSuggestionsVisible();
            fetchSuggestionsForField(true);
        });

        field.addEventListener('input', function () {
            if (debounceTimer) {
                window.clearTimeout(debounceTimer);
            }
            debounceTimer = window.setTimeout(function () {
                fetchSuggestionsForField(false);
            }, 120);
        });
    }

    function wireFreeAddressAutocomplete(scope) {
        var root = scope || document;
        root.querySelectorAll('input[name="home_address"], #id_home_address, #editHomeAddress, #infoHomeAddress, [data-address-autocomplete="1"]').forEach(function (field) {
            wireFreeAddressAutocompleteField(field);
        });
    }

    function enhance(root) {
        var scope = root || document;
        scope.querySelectorAll('form').forEach(wireFormValidation);
        scope.querySelectorAll('input[type="password"]').forEach(wirePasswordToggle);
        scope.querySelectorAll('.js-captcha-refresh').forEach(wireCaptchaRefresh);
        wireFreeAddressAutocomplete(scope);
    }

    document.addEventListener('DOMContentLoaded', function () {
        enhance(document);

        document.addEventListener('click', function (event) {
            var button = event.target.closest ? event.target.closest('.js-captcha-refresh') : null;
            if (!button) {
                return;
            }
            event.preventDefault();
            refreshCaptcha(button);
        });

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (!(node instanceof Element)) {
                        return;
                    }
                    if (node.matches && (node.matches('form') || node.matches('input[type="password"]'))) {
                        enhance(node.parentElement || document);
                    } else if (node.querySelectorAll) {
                        enhance(node);
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    });

    window.AvantechFormEnhancer = {
        enhance: enhance,
    };
})();
