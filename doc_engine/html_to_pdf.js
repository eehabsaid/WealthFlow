const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function generatePDF() {
    if (process.argv.length < 4) {
        console.error("Usage: node html_to_pdf.js <input_html> <output_pdf>");
        process.exit(1);
    }

    const inputHtml = path.resolve(process.argv[2]);
    const outputPdf = path.resolve(process.argv[3]);

    if (!fs.existsSync(inputHtml)) {
        console.error(`Input file not found: ${inputHtml}`);
        process.exit(1);
    }

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
        // Load the HTML file
        await page.goto(`file://${inputHtml}`, { waitUntil: 'networkidle' });

        // Wait for fonts to load
        await page.evaluate(() => document.fonts.ready);

        // Ensure all images are loaded
        await page.evaluate(async () => {
            const images = Array.from(document.querySelectorAll('img'));
            await Promise.all(images.map(img => {
                if (img.complete) return;
                return new Promise((resolve, reject) => {
                    img.addEventListener('load', resolve);
                    img.addEventListener('error', resolve); // resolve on error to not block PDF
                });
            }));
        });

        // Generate PDF
        await page.pdf({
            path: outputPdf,
            format: 'A4',
            printBackground: true,
            margin: {
                top: '20mm',
                right: '20mm',
                bottom: '20mm',
                left: '20mm'
            },
            displayHeaderFooter: true,
            headerTemplate: '<div style="font-size: 10px; width: 100%; text-align: center; color: #6c757d;">WealthFlow Documentation</div>',
            footerTemplate: '<div style="font-size: 10px; width: 100%; text-align: center; color: #6c757d;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
        });

        console.log(`Generated PDF: ${outputPdf}`);
    } catch (error) {
        console.error("PDF Generation failed:", error);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

generatePDF();
