function downloadPDF(){

  updateCertificate();

  const element = document.getElementById("cert");

  html2pdf().from(element).save("GreenTrack-Certificate.pdf");

}