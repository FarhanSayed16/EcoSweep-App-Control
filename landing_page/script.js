// script.js
document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add a slight hover effect to the download button that tracks mouse position
    const downloadBtn = document.getElementById('downloadBtn');
    
    downloadBtn.addEventListener('mousemove', (e) => {
        const rect = downloadBtn.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Optionally use these coordinates to create a spotlight effect in CSS
        downloadBtn.style.setProperty('--mouse-x', `${x}px`);
        downloadBtn.style.setProperty('--mouse-y', `${y}px`);
    });
});
