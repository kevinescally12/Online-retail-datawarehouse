document.querySelectorAll('.sidebar-nav a').forEach(link => {
  link.addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth < 992 && window.bootstrap) window.bootstrap.Offcanvas.getInstance(sidebar)?.hide();
  });
});
