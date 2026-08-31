document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-upload');
    const dropzone = document.querySelector('.upload__dropzone');
    const linkInput = document.querySelector('.upload__input');
    const copyButton = document.querySelector('.upload__copy');

    const uploadFile = (file) => {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData,
        })
            .then((response) => {
                if (!response.ok) {
                    return response.text().then((text) => { throw new Error(text); });
                }
                return response.text();
            })
            .then((link) => {
                linkInput.value = link;
            })
            .catch((err) => {
                alert('Помилка завантаження: ' + err.message);
            });
    };

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadFile(file);
        }
        event.target.value = '';
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    dropzone.addEventListener('drop', (event) => {
        const file = event.dataTransfer.files[0];
        if (file) {
            uploadFile(file);
        }
    });

    if (copyButton && linkInput) {
        copyButton.addEventListener('click', () => {
            if (linkInput.value) {
                navigator.clipboard.writeText(linkInput.value).then(() => {
                    copyButton.textContent = 'COPIED!';
                    setTimeout(() => { copyButton.textContent = 'COPY'; }, 2000);
                });
            }
        });
    }
});
