//Duong Doan Tung 21010294

//Project completion rate:
// Arduino: 100%
// RPI: 70%

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
//#define SERIAL_DEBUG

#pragma region Global Variables
const char rows = 4; // set display to four rows
const char cols = 4; // set display to four columns
#define DELAY_BETWEEN_BTN 500 // 0.5 seconds
#define DOOR_LED 11
#define FACE_LED 12
const char keys[rows][cols] = {
			   {'1','2','3','A'},
			   {'4','5','6','B'},
			   {'7','8','9','C'},
			   {'*','0','#','D'}
};

char rowPins[rows] = { 3,4,5,6 };
char colPins[cols] = { 10,9,8,7 };
volatile bool reverse = false;
float DELAY_TIME = 1;
volatile uint32_t preloader = 57722;
volatile bool update = false;
static int speed = 0;
static int doorOpenTime = 60000;
static int doorHeight = 200; // Step take to open the door
volatile int doorStep = 0; // Current step of the door
int last_value = 0;
uint8_t stage = 0;
uint8_t mode = 0;
uint8_t count = 0;
volatile long last_btn_time = 0;
float current_count = 0;
LiquidCrystal_I2C lcd(0x27, 16, 2);
enum Mode { WAVE = 0, FULL = 1, HALF = 2 };
volatile uint8_t calibrate_count = 0; //0 is not calibrating, 1 is closing, 2 is opening
volatile bool calibrating = false;
volatile unsigned long access_session_start_time = 0;
const uint16_t serial_check_routine = 1;
long last_serial_check_time = 0;

const uint8_t STAGES[3][8] = {
	//wave stages
	 {0x01, 0x02, 0x04, 0x08, 0x01, 0x02, 0x04, 0x08},
	 //full stages
	 {0x03, 0x06, 0x0C, 0x09, 0x03, 0x06, 0x0C, 0x09},
	 //half stages
	 {0x01, 0x03, 0x02, 0x06, 0x04, 0x0C, 0x08, 0x09}
};
const uint32_t STEP_PER_ROUND[3] = { 2048, 2048, 2048 };
// Arduino is used to get password, then send it to RPI, RPI will check if the password is correct
//RPI then send command to open the door or setting variable of arduino
enum Command {
	SEND_KEY = 'K', // send pressed key to RPI
	DISPLAY_MESSAGE = 'D', // display message on LCD
	GRANT_ACCESS = 'G', // grant access to open the door
	CLOSE_DOOR = 'L', // close the door
	FACE_DETECTED = 'F', // face detected
	END = '_', //end current command
	READY = 'R', // ready to receive command
	//setting variable
	SET_ACCESS_TIME = 'A',
	SET_SPEED = 'E', // set speed
	SET_OPENTIME = 'T', // set door open time
	CALIBRATING = 'C', // Close the door till button is pressed, then start counting step take to open the door (button is pressed again)
	SET_CALIBRATING_VALUE = 'V', // set the value of door steps
	GET_CALIBRATING_VALUE = 'S', // get the value of door steps
};
enum DoorState {
	DOOR_OPEN = 'O',
	DOOR_CLOSE = 'C',
	DOOR_OPENING = 'I',
	DOOR_CLOSING = 'L',
};

volatile int doorState = DOOR_CLOSE;

#pragma endregion
void openDoor();
void closeDoor();
#pragma region Interrupts

ISR(INT0_vect) {
	//TBA -> open door
	if (millis() - last_btn_time < DELAY_BETWEEN_BTN) return;
	//if calibrating, move to next step
	if (calibrating)
	{
		calibrate_count++;
	}
	else
	{
		if (doorState == DOOR_CLOSE || doorState == DOOR_CLOSING)
		{
			openDoor();
		}
		else if (doorState == DOOR_OPEN || doorState == DOOR_OPENING)
		{
			closeDoor();
		}
	}

	last_btn_time = millis();
}
ISR(TIMER1_OVF_vect)
{
	//Serial.println(preloader);
	TCNT1 = preloader;
	if (doorStep == 0 && !(calibrating && calibrate_count > 0)) return;
	digitalWrite(DOOR_LED, HIGH);
	PORTC = (PORTC & 0b110000) | (STAGES[mode][stage]);
	if (doorState == DOOR_OPENING)
	{
		if (stage == 0)
			stage = 7;
		else
			stage--;
	}
	else if (doorState == DOOR_CLOSING)
	{
		if (stage == 7)
			stage = 0;
		else
			stage++;
	}
	if (calibrating) doorStep++;
	else doorStep--;
}
#pragma endregion

#pragma region Functions
char getKey() {
	char k = 0;

	for (char c = 0; c < cols; c++) {
		digitalWrite(colPins[c], LOW);
		for (char r = 0; r < rows; r++) {
			//print the matrix with the pressed key highlighted
			if (digitalRead(rowPins[r]) == LOW) {
				while (digitalRead(rowPins[r]) == LOW);
				k = keys[r][c];
#ifdef SERIAL_DEBUG
				Serial.print("1 ");
#endif
			}
			else {
#ifdef SERIAL_DEBUG
				Serial.print("0 ");
#endif
			}
		}
#ifdef SERIAL_DEBUG
		Serial.println();
#endif
		digitalWrite(colPins[c], HIGH);
	}
#ifdef SERIAL_DEBUG
	Serial.println('\n');
#endif

	return k;
}
void openDoor() {
	if (doorState == DOOR_OPENING || doorState == DOOR_OPEN) return;
	doorState = DOOR_OPENING;
	if (doorStep == 0)
		doorStep = doorHeight;
	else doorStep = doorHeight - doorStep;
	/*lcd.clear();
	lcd.setCursor(0, 0);
	lcd.print("Opening door...");*/
}

void closeDoor() {
	if (doorState == DOOR_CLOSING || doorState == DOOR_CLOSE) return;
	doorState = DOOR_CLOSING;
	if (doorStep == 0)
		doorStep = doorHeight;
	else doorStep = doorHeight - doorStep;
	/*lcd.clear();
	lcd.setCursor(0, 0);
	lcd.print("Closing door..");*/
}
int calibrate() {
	calibrating = true;
	lcd.clear();
	lcd.setCursor(0, 0);
	lcd.print("Calibrating...");
	lcd.setCursor(0, 1);
	while (calibrate_count < 6) {
		if (calibrate_count == 1) {
			doorStep = 0;
			doorState = DOOR_CLOSING;
			calibrate_count++;
		}
		else if (calibrate_count == 3) {
			doorStep = 0;
			doorState = DOOR_OPENING;
			calibrate_count++;
		}
		else if (calibrate_count == 5) {
			doorHeight = doorStep;
			doorState = DOOR_OPEN;
			calibrate_count++;
		}
	}
	calibrating = false;
	calibrate_count = 0;
	lcd.clear();
	lcd.setCursor(0, 0);
	lcd.print("Calibrated");
	lcd.setCursor(0, 1);
	lcd.print("Steps: ");
	lcd.print(doorHeight);
	delay(5000);
	lcd.clear();
	return doorHeight;
}

void getCommand() {
cont:
	//Serial.println((char)READY);
	//get serial command from RPI, should be in format: <command><value>
	char command;
	String value = "";
	//read the first char and store it in command
	String tmp = Serial.readStringUntil('\n');
	//Seperate the first char to command
	command = tmp[0];
	//Seperate the rest of the string to value
	value = tmp.substring(1);
	if (command == 0) goto cont;
	//Print back the received command and value
#ifdef SERIAL_DEBUG
	Serial.print("Command: ");
	Serial.println(command);
	Serial.print("Value: ");
	Serial.println(value);
#endif
	switch ((int)command)
	{
	case SEND_KEY:
		break;
	case DISPLAY_MESSAGE:
		lcd.clear();
		lcd.setCursor(0, 0);
		lcd.print(value.substring(0, 16));
		lcd.setCursor(0, 1);
		lcd.print(value.substring(16));
		break;
	case GRANT_ACCESS:
		openDoor();
		break;
	case CLOSE_DOOR:
		closeDoor();
		break;
	case FACE_DETECTED:
		if (value.charAt(0) == 'D')
			digitalWrite(FACE_LED, HIGH);
		else if (value.charAt(0) == 'U')
			digitalWrite(FACE_LED, LOW);
		break;
	case SET_ACCESS_TIME:
		doorOpenTime = value.toInt();
		break;
	case SET_SPEED:
		if (value.toInt() > 0)
			preloader = value.toInt();
		break;
	case SET_OPENTIME:
		if (value.toInt() > 0)
			doorOpenTime = value.toInt();
		break;
	case CALIBRATING:
		calibrate();
		break;
	case END:
		return;
	case SET_CALIBRATING_VALUE:
		doorHeight = value.toInt();
	case GET_CALIBRATING_VALUE:
		Serial.print("V");
		//doorHeight to string
		Serial.println(doorHeight);
	default:
		break;
	}
	goto cont;
}

void sendKey(char key) {
	//send key to RPI, should be in format: <command><value>\n
	String tosend = "";
	//add command
	tosend += (char)SEND_KEY;
	//add value
	tosend += key;
	//add new line
	tosend += '\n';
	//send to RPI
	Serial.print(tosend);
}

#pragma endregion

void setup() {
	Serial.begin(9600);
	//disable all interrupt
	noInterrupts();
	EICRA |= 0x02;
	EIMSK |= 0x01;
	//set PORTC as output for A0, A1, A2, A3 only, leave A4, A5 as default
	DDRC |= B00001111; // set bits 0-3 to 1
	TCCR1A = 0x00;
	TCCR1B = 0x00;
	DELAY_TIME = 0.015625; // set default delay time
	preloader = 65535 - (16000000.f * DELAY_TIME / 8.0f);
	TCNT1 = preloader;
	TCCR1B = 0x02; // set Timer1 clock source to system clock divided by 256
	TIMSK1 |= 0x01;
	interrupts();
	for (char r = 0; r < rows; r++) {
		pinMode(rowPins[r], INPUT);        //set the row pins as input
		digitalWrite(rowPins[r], HIGH);    //turn on the pullups
	}

	for (char c = 0; c < cols; c++) {
		pinMode(colPins[c], OUTPUT);       //set the column pins as output
	}
	pinMode(DOOR_LED, OUTPUT);
	pinMode(FACE_LED, OUTPUT);
	lcd.backlight();
	lcd.init();
	lcd.print("Waiting for RPi");
	lcd.setCursor(0, 1);
	lcd.print("Loading config..");
	getCommand();
	delay(100);
	lcd.clear();
	lcd.home();
	lcd.print("Init complete");
	delay(1000);
	lcd.clear();
	//calibrate();
}

void loop() {
	char key = getKey();
	if (key != 0) {
		sendKey(key);
		getCommand();
	}

	if (doorState == DOOR_OPEN && millis() - access_session_start_time > doorOpenTime) {
		closeDoor();
	}
	else if (doorState == DOOR_OPEN && millis() - access_session_start_time > (doorOpenTime * 0.2) && (millis() - access_session_start_time) / 100 % 10 == 0)
	{
		lcd.clear();
		lcd.setCursor(0, 0);
		lcd.print("Door close in:");
		lcd.setCursor(0, 1);
		int num = round((doorOpenTime + access_session_start_time - millis()) / 1000);
		lcd.print(num > 9999 || num < 0 ? 0 : num);
		lcd.setCursor(8, 1);
		lcd.print("seconds");
	}
	if (doorStep == 0)
	{
		if (doorState == DOOR_OPENING)
		{
			doorState = DOOR_OPEN;
			access_session_start_time = millis();
			lcd.clear();
			lcd.setCursor(0, 0);
			lcd.print("Access granted");
		}
		else if (doorState == DOOR_CLOSING)
		{
			doorState = DOOR_CLOSE;
			lcd.clear();
			lcd.setCursor(0, 0);
			lcd.print("Enter password:");
			lcd.setCursor(0, 1);
			lcd.print("____");
		}
		digitalWrite(DOOR_LED, LOW);
		PORTC = (PORTC & 0b110000) | (0);
	}
	if (millis() - last_serial_check_time > serial_check_routine)
	{
		last_serial_check_time = millis();
		String tosend = "";
		tosend += (char)END;
		tosend += '\n';
		Serial.print(tosend);
		getCommand();
	}
}