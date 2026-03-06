/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.py",
    "./src/**/*.html",
    "./exports/**/*.html"
  ],
  theme: {
    extend: {
      borderRadius: {
        '2xl': '1rem'
      }
    }
  },
  plugins: []
};
