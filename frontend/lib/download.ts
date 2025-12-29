export const forceDownload = async (url: string, filename: string) => {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);

        const anchor = document.createElement('a');
        anchor.href = blobUrl;
        anchor.download = filename;
        anchor.style.display = 'none'; // Silent
        document.body.appendChild(anchor);

        anchor.click();

        // Cleanup
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(blobUrl);
        return true;
    } catch (e) {
        console.error("Silent download failed:", e);
        // Fallback: Open in new tab if silent fail (but user wants strict SPA, so maybe just alert?)
        // Attempting standard download approach if CORS fails might be needed, but for now strict blob.
        return false;
    }
};
