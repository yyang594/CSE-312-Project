async function handleUploadPfp(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    try {
        const response = await fetch('/profile/upload', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const res = await response.json();
            if (res.status === 'ok') {
                alert(res.message || 'File uploaded successfully!');
                // Update displayed pfp if new URL is returned
                if (res.profile_picture) {
                    const profileImage = document.getElementById('profilePicture');
                    if (profileImage) {
                        profileImage.src = res.profile_picture;
                    }
                }
            }
        } else {
            const errorText = await response.text();
            console.error('Upload failed. Server responded with:', errorText);
            alert('Upload failed.');
        }
    } catch (error) {
        console.error('Error during upload:', error);
        alert('Error occurred. Please try again.');
    }
}