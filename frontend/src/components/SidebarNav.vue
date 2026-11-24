<template>
  <aside class="sidebar">
    <RouterLink class="brand" :to="{ name: 'catalog' }" aria-label="Ir al catálogo">
      <span class="brand__mark" aria-hidden="true">
        <svg viewBox="0 0 32 32">
          <path d="M6 6.5A3.5 3.5 0 0 1 9.5 3H27v23H9.5A3.5 3.5 0 0 0 6 29z" />
          <path d="M6 6.5v22A3.5 3.5 0 0 1 9.5 25H27M12 9h10M12 14h10" />
        </svg>
      </span>
      <span class="brand__text">
        <strong>Biblioteca</strong>
        <small>Biblioteca digital</small>
      </span>
    </RouterLink>

    <div class="sidebar__section-label">ESPACIO DE TRABAJO</div>
    <nav class="sidebar-nav" aria-label="Navegación principal">
      <RouterLink class="sidebar-nav__link" :to="{ name: 'catalog' }" exact-active-class="is-active">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22z" />
          <path d="M4 5.5v16.5A2.5 2.5 0 0 1 6.5 20H20M8 7h8M8 11h8" />
        </svg>
        <span>Catálogo</span>
      </RouterLink>
    </nav>

    <div class="sidebar__bottom">
      <div class="sidebar__note-icon" aria-hidden="true">✦</div>
      <p>Un buen libro siempre encuentra su lector.</p>
      <span>GESTIÓN BIBLIOTECARIA</span>
    </div>
  </aside>
</template>
