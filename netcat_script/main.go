package main

import (
	"fmt"
	"os/exec"
	"strings"

	log "github.com/sirupsen/logrus"
)

func main() {
    message := "my_message"
	command := fmt.Sprintf("echo %s | nc -N server 12345", message)
	// out, err := exec.Command(command).Output()
	// out, err := exec.Command("nc", "-N", "server", "12345", message).Output()
	out, err := exec.Command("sh", "-c", command).Output()
    if err != nil {
        log.Fatal(err)
    }
	string_answer := string(out[:])
	if (strings.TrimRight(string_answer, "\n") == fmt.Sprintf("Your Message has been received: %s", message)) {
		fmt.Println("Message echoed successfully:")
	} else {
		fmt.Println("Error in message echoing:")
	}
	fmt.Printf("Message sent: %s\n", message)
	fmt.Printf("Message received: %s\n", string_answer)
}
