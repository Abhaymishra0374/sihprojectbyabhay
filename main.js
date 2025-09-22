// scripts.js

// Example: Confirm before submitting waste form
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  if (form && form.action.includes("submit_waste")) {
    form.addEventListener("submit", (e) => {
      const confirmSubmit = confirm("Are you sure you want to submit this waste record?");
      if (!confirmSubmit) {
        e.preventDefault();
      }
    });
  }
});
