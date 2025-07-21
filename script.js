document.addEventListener('DOMContentLoaded', () => {

    const API_URL = "http://127.0.0.1:8000/api";

    // Elementos del DOM
    const navLogo = document.querySelector('.nav-logo');
    const navLinks = document.querySelectorAll('.nav-link');
    const views = document.querySelectorAll('.view');
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const regionFilters = document.getElementById('region-filters');
    const countriesGrid = document.getElementById('countries-grid');
    const savedCountriesGrid = document.getElementById('saved-countries-grid');
    const modalContainer = document.getElementById('item-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalAddBtn = document.getElementById('modal-add-btn');
    const modalDeleteBtn = document.getElementById('modal-delete-btn');

    // Manejo de las vistas
    function switchView(viewName) {
        views.forEach(view => view.classList.add('hidden'));
        const activeView = document.getElementById(`view-${viewName}`);
        if (activeView) activeView.classList.remove('hidden');
        
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.view === viewName);
        });
        
        if (viewName === 'browse' && countriesGrid.childElementCount === 0) {
            fetchCountriesByRegion('all');
        }
        if (viewName === 'local') {
            displaySavedCountries();
        }
    }

    navLinks.forEach(link => link.addEventListener('click', (e) => { e.preventDefault(); switchView(e.target.dataset.view); }));
    navLogo.addEventListener('click', (e) => { e.preventDefault(); switchView('home'); });

    // Búsqueda y filtros
    searchButton.addEventListener('click', () => {
        const query = searchInput.value.trim();
        if (query) {
            fetchCountriesByName(query);
        }
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchButton.click();
        }
    });

    regionFilters.addEventListener('click', (e) => {
        if (e.target.classList.contains('region-button')) {
            const region = e.target.dataset.region;
            const subregion = e.target.dataset.subregion;

            document.querySelector('.region-button.active')?.classList.remove('active');
            e.target.classList.add('active');

            if (region) {
                fetchCountriesByRegion(region);
            } else if (subregion) {
                fetchCountriesBySubregion(subregion);
            }
        }
    });

    async function fetchCountriesByRegion(region) {
        const endpoint = region === 'all' ? '/countries/all' : `/countries/by-region/${region}`;
        fetchAndDisplayCountries(endpoint);
    }
    
    async function fetchCountriesBySubregion(subregion) {
        fetchAndDisplayCountries(`/countries/by-subregion/${subregion}`);
    }
    
    async function fetchCountriesByName(name) {
        fetchAndDisplayCountries(`/countries/by-name/${name}`);
    }

    async function fetchAndDisplayCountries(endpoint) {
        countriesGrid.innerHTML = '<p class="loading-text">Cargando países...</p>';
        try {
            const response = await fetch(`${API_URL}${endpoint}`);
            if (!response.ok) throw new Error('No se encontraron países con ese criterio.');
            const countries = await response.json();
            countriesGrid.innerHTML = '';
            countries.forEach(country => createCard(country, countriesGrid, 'browse'));
        } catch (error) {
            countriesGrid.innerHTML = `<p class="error-text">${error.message}</p>`;
        }
    }

    // Tarjetas y modal
    function createCard(country, container, source = 'browse') {
        const card = document.createElement('div');
        card.className = 'card';
        const flagUrl = country.flags ? country.flags.png : country.flag_url;
        const countryName = country.name.common ? country.name.common : country.name;

        card.innerHTML = `
            <img src="${flagUrl}" class="card-img" alt="Bandera de ${countryName}">
            <div class="card-body">
                <h3>${countryName}</h3>
            </div>
        `;
        card.addEventListener('click', () => openModal(country.cca3, source === 'local'));
        container.appendChild(card);
    }

    async function openModal(countryCode, isFromSavedView = false) {
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = '<p class="loading-text">Cargando detalles...</p>';
        
        if (isFromSavedView) {
            modalAddBtn.classList.add('hidden');
            modalDeleteBtn.classList.remove('hidden');
            modalDeleteBtn.onclick = () => deleteCountry(countryCode);
        } else {
            modalAddBtn.classList.remove('hidden');
            modalDeleteBtn.classList.add('hidden');
        }

        modalContainer.classList.remove('hidden');
        try {
            const response = await fetch(`${API_URL}/country/${countryCode}`);
            if (!response.ok) throw new Error('No se pudieron cargar los detalles.');
            
            const country = await response.json();
            const capital = country.capital ? country.capital[0] : 'N/A';
            const currency = country.currencies ? Object.values(country.currencies)[0].name : 'N/A';
            const language = country.languages ? Object.values(country.languages)[0] : 'N/A';

            modalBody.innerHTML = `
                <h2>${country.name.common}</h2>
                <p><strong>Capital:</strong> ${capital}</p>
                <p><strong>Población:</strong> ${country.population.toLocaleString('es-CR')}</p>
                <p><strong>Región:</strong> ${country.region}</p>
                <p><strong>Moneda:</strong> ${currency}</p>
                <p><strong>Idioma Principal:</strong> ${language}</p>
            `;
            
            if (!isFromSavedView) {
                modalAddBtn.onclick = () => saveCountry(country);
            }
        } catch (error) {
            modalBody.innerHTML = `<p class="error-text">${error.message}</p>`;
        }
    }
    
    function closeModal() {
        modalContainer.classList.add('hidden');
    }
    
    modalCloseBtn.addEventListener('click', closeModal);
    modalContainer.addEventListener('click', (event) => {
        if (event.target === modalContainer) {
            closeModal();
        }
    });

    // BD
    async function saveCountry(country) {
        const countryData = {
            cca3: country.cca3,
            name: country.name.common,
            region: country.region,
            flag_url: country.flags.png 
        };
        try {
            const response = await fetch(`${API_URL}/save-country`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(countryData),
            });
            const result = await response.json();
            alert(result.message);
            closeModal();
        } catch (error) {
            alert("⚠️ Error al guardar el país.");
        }
    }

    async function displaySavedCountries() {
        savedCountriesGrid.innerHTML = '<p class="loading-text">Cargando países guardados...</p>';
        try {
            const response = await fetch(`${API_URL}/saved-countries`);
            if(!response.ok) throw new Error("No se pudo conectar a la base de datos.");
            
            const countries = await response.json();
            savedCountriesGrid.innerHTML = '';
            
            if (countries.length === 0) {
                savedCountriesGrid.innerHTML = `<p class="placeholder-text">No has guardado ningún país todavía.</p>`;
                return;
            }

            countries.forEach(country => {
                createCard(country, savedCountriesGrid, 'local');
            });
        } catch (error) {
            savedCountriesGrid.innerHTML = `<p class="error-text">${error.message}</p>`;
        }
    }

    async function deleteCountry(cca3) {
        if (!confirm("¿Estás seguro de que quieres eliminar este país de tu lista?")) {
            return;
        }
        try {
            const response = await fetch(`${API_URL}/delete-country/${cca3}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "No se pudo eliminar el país.");
            }
            const result = await response.json();
            alert(result.message);
            closeModal();
            displaySavedCountries(); 
        } catch (error) {
            alert(`⚠️ Error al eliminar: ${error.message}`);
        }
    }

    switchView('home');
});