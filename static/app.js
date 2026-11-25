function closeMenus(except) {
  document.querySelectorAll('.action-menu.open').forEach(function(menu) {
    if (menu !== except) {
      menu.classList.remove('open');
      const b = menu.querySelector('.dots');
      if (b) b.setAttribute('aria-expanded', 'false');
    }
  });
}
function toggleMenu(button) {
  const menu = button.closest('.action-menu');
  const willOpen = !menu.classList.contains('open');
  closeMenus(menu);
  menu.classList.toggle('open', willOpen);
  button.setAttribute('aria-expanded', String(willOpen));
}
document.addEventListener('click', function(event) {
  if (!event.target.closest('.action-menu')) closeMenus(null);
});
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') closeMenus(null);
});
