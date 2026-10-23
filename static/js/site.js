// Лише необов’язкове підтвердження. Усі дії виконуються звичайним POST-запитом.
document.addEventListener('submit', (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
