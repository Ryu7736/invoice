const InputImageElement = document.querySelector("#InputImage");
const ocrElement = document.querySelector("#ocr");
const resultElement = document.querySelector("#result");
const clickedElement = document.querySelector("#clicked");

ocrElement.addEventListener("click", async () => {
    if(InputImageElement.files.length === 0) {
        alert("ファイルを選択してください")
        return
    }

    const fd = new FormData();
    for (const file of InputImageElement.files) {
        fd.append("files", file);
    }

    const response = await fetch("/uploads", { method: "POST", body: fd })
    // if (!response.ok) {
    //     alert("!response.ok");
    // }
    const data = await response.json();
    resultElement.innerHTML = JSON.stringify(data.ocr_results,null,2);
});