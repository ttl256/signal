(() => {
    const root = document.documentElement;
    const images = document.querySelectorAll("img[data-src-dark]");
    if (!images.length) return;

    function updateFigures() {
        const dark = root.dataset.theme === "dark";
        for (const image of images) {
            const src = dark ? image.dataset.srcDark : image.dataset.srcLight;
            if (image.getAttribute("src") !== src) image.setAttribute("src", src);

            const link = image.closest("a[data-link-dark]");
            if (link) {
                link.setAttribute("href", dark ? link.dataset.linkDark : link.dataset.linkLight);
            }
        }
    }

    updateFigures();
    // PaperMod sets data-theme on initial load and whenever its toggle is used.
    new MutationObserver(updateFigures).observe(root, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });
})();
