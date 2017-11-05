var express = require('express');
var app = express();

// Create the bounding boxes
var numBoxes = 400;
var boxes = []
for(var i = 0; i < numBoxes; i++){
	var xVal = Math.floor(Math.random() * 500);
	var yVal = Math.floor(Math.random() * 500);
	var nameVal = "abcd";
	var box = {"x" : xVal, "y" : yVal, "name" : nameVal};
	boxes.push(box);
}

// Default route
app.get('*', function(req, res){
	// Send JSON data back	
	res.setHeader("Content-Type", "application/json");
	var json = {"boxes" : boxes};

	res.send(JSON.stringify(json));

	// Randomly change locations
	for(var i = 0; i < boxes.length; i++){
		boxes[i]["x"] += (Math.floor(Math.random() * 3)) - 1;
		boxes[i]["y"] += (Math.floor(Math.random() * 3)) - 1;
	}

});

console.log("Listening on 8000");
app.listen(8000);
