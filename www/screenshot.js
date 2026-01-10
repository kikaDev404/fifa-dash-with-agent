// function takeScreenshot() {
//     console.log("Starting screenshot capture...");

//     html2canvas(document.body, {
//         useCORS: true,
//         logging: true
//     })
//     .then(canvas => {
//         const base64image = canvas.toDataURL("image/png");
//         Shiny.setInputValue("screenshot_data", base64image, { priority: "event" });
//     })
//     .catch(err => {
//         console.error("Screenshot failed:", err);
//     });

//     console.log("Finished taking the screenshot")
// }

// Shiny.addCustomMessageHandler("take_screenshot", (msg) => {
//     takeScreenshot();
// });

// Function to capture screenshot
async function takeScreenshot() {
    try {
        const canvas = await html2canvas(document.body, {
            useCORS: true,
            logging: true,
            scrollY: -window.scrollY,
            scrollX: -window.scrollX
        });
        const base64image = canvas.toDataURL("image/png");
        return base64image;
    } catch (err) {
        console.error("Screenshot failed:", err);
        return null;
    }
}

// Sends screenshot to Shiny reactive input
async function sendScreenshotToShiny() {
    const base64image = await takeScreenshot();
    if (base64image) {
        Shiny.setInputValue("screenshot_data", base64image, { priority: "event" });
    } else {
        Shiny.setInputValue("screenshot_data", null, { priority: "event" });
    }
}

// Shiny message handler
Shiny.addCustomMessageHandler("take_screenshot", (msg) => {
    sendScreenshotToShiny();
});

