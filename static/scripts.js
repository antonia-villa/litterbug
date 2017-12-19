// JavaScript Functions

// Dynamically Color Table Values based on Bag Status
$(document).ready(function(){
    $('#table_id td.saved_used').each(function(){
        // Transactions with Saved Bags
        if ($(this).text() == 'SAVED') {
            $(this).css('color','#088A29');
        }
        // Transactions with Used Bags
        else{
            $(this).css('color','#B40404');
        }
    });
});


// Create link for clickable row for table
$(document).ready(function($) {
    $(".clickable-row").click(function() {
        window.document.location = $(this).data("href");
    });
});

// Create pop-up window
$(document).ready(function(){
  
  // Hover
  $("#hover").click(function(){
		$(this).fadeOut();
    $("#popup").fadeOut();
	});
  
  // Close Window
  $("#close").click(function(){
		$("#hover").fadeOut();
    $("#popup").fadeOut();
	});
  
});

// Function to go back
function goBack() {
    window.history.back();
}