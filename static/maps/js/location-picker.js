(function () {
    function parseCoordinate(value, fallback) {
        if (value === undefined || value === null || value === '') {
            return fallback;
        }
        const normalized = String(value).trim().replace(',', '.');
        const parsed = Number.parseFloat(normalized);
        return Number.isNaN(parsed) ? fallback : parsed;
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (const cookie of cookies) {
            const item = cookie.trim();
            if (item.startsWith(name + '=')) {
                return decodeURIComponent(item.slice(name.length + 1));
            }
        }
        return '';
    }

    class LeafletLocationPicker {
        constructor(rootElement) {
            this.root = rootElement;
            this.mapId = this.root.dataset.mapId;
            this.endpoint = this.root.dataset.endpoint;
            this.latInput = document.getElementById(this.root.dataset.latInputId);
            this.lngInput = document.getElementById(this.root.dataset.lngInputId);
            this.addressInput = document.getElementById(this.root.dataset.addressInputId);
            this.feedback = this.root.querySelector('.js-map-feedback');
            this.latPreview = this.root.querySelector('.js-lat-value');
            this.lngPreview = this.root.querySelector('.js-lng-value');
            this.addressPreview = this.root.querySelector('.js-address-value');
            this.useLocationButton = this.root.querySelector('.js-use-current-location');
            this.marker = null;
            this.map = null;
        }

        init() {
            if (!window.L) {
                this.updateFeedback('Falha ao carregar Leaflet.', true);
                return;
            }

            const initialLat = parseCoordinate(
                this.latInput?.value || this.root.dataset.initialLat,
                -14.2350
            );
            const initialLng = parseCoordinate(
                this.lngInput?.value || this.root.dataset.initialLng,
                -51.9253
            );
            const initialZoom = parseInt(this.root.dataset.initialZoom || '5', 10);

            this.map = L.map(this.mapId).setView([initialLat, initialLng], initialZoom);

            // Troca futura de provider de tiles:
            // altere apenas data-tile-url no template ou no dataset deste componente.
            L.tileLayer(this.root.dataset.tileUrl, {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap contributors',
            }).addTo(this.map);

            if (this.addressInput?.value) {
                this.addressPreview.textContent = this.addressInput.value;
            }

            if (this.latInput?.value && this.lngInput?.value) {
                this.setPoint(initialLat, initialLng, false);
            }

            this.map.on('click', (event) => {
                this.setPoint(event.latlng.lat, event.latlng.lng, true);
            });

            this.useLocationButton?.addEventListener('click', () => this.useCurrentLocation());
        }

        setPoint(lat, lng, notifyBackend) {
            const normalizedLat = Number(lat.toFixed(6));
            const normalizedLng = Number(lng.toFixed(6));

            if (!this.marker) {
                this.marker = L.marker([normalizedLat, normalizedLng]).addTo(this.map);
            } else {
                this.marker.setLatLng([normalizedLat, normalizedLng]);
            }

            const popupText = `Lat: ${normalizedLat} | Lng: ${normalizedLng}`;
            this.marker.bindPopup(popupText).openPopup();

            if (this.latInput) this.latInput.value = String(normalizedLat);
            if (this.lngInput) this.lngInput.value = String(normalizedLng);
            this.latPreview.textContent = String(normalizedLat);
            this.lngPreview.textContent = String(normalizedLng);
            this.updateFeedback('Coordenadas selecionadas.');

            this.map.panTo([normalizedLat, normalizedLng]);

            if (notifyBackend) {
                this.sendCoordinates(normalizedLat, normalizedLng);
            }
        }

        async sendCoordinates(latitude, longitude) {
            this.root.classList.add('is-loading');
            this.updateFeedback('Processando localização...');

            try {
                const response = await fetch(this.endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        latitude,
                        longitude,
                        include_address: true,
                    }),
                });

                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Não foi possível processar a localização.');
                }

                const address = payload.address || 'Endereço não identificado';
                this.addressPreview.textContent = address;
                if (this.addressInput) this.addressInput.value = address;
                this.updateFeedback('Localização validada com sucesso.');
            } catch (error) {
                this.updateFeedback(error.message, true);
            } finally {
                this.root.classList.remove('is-loading');
            }
        }

        useCurrentLocation() {
            if (!navigator.geolocation) {
                this.updateFeedback('Geolocalização não suportada neste navegador.', true);
                return;
            }

            this.updateFeedback('Obtendo localização atual...');
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    this.map.setView([latitude, longitude], 12);
                    this.setPoint(latitude, longitude, true);
                },
                () => {
                    this.updateFeedback('Não foi possível obter sua localização.', true);
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        }

        updateFeedback(message, isError) {
            this.feedback.textContent = message;
            this.feedback.classList.toggle('error', Boolean(isError));
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const widgets = document.querySelectorAll('.js-location-picker');
        widgets.forEach((widget) => {
            const picker = new LeafletLocationPicker(widget);
            picker.init();
        });
    });
})();
