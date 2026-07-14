const fs = require('fs');

const content = fs.readFileSync('user-review-dashboard/index.html', 'utf-8');

console.log("Empty modal label?", content.includes('aria-label="Modal"'));
console.log("Modal focus?", content.includes('tabindex="0"'));
console.log("Tooltip ARIA labels?", content.includes('aria-label="View Data Source"'));
