package common

import (
	// "bufio"
	// "fmt"
	// "net"
	"time"
	"os"
    "os/signal"
    "syscall"

	log "github.com/sirupsen/logrus"
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopLapse     time.Duration
	LoopPeriod    time.Duration
	DatasetPath   string
	BatchSize     uint32
	RequestAwait  uint32
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	manager   *ParticipantsManager
}

func logErrorMessage(id string, err error) {
	log.Fatalf(
		"[CLIENT %v] Error: %v",
		id,
		err,
	)
}

func closeParticipantsManager(client *Client) error {
	err := client.manager.CloseConnection()
	if err != nil {
		log.Fatalf(
			"[CLIENT %v] Could not close socket connection. Error: %v",
			client.config.ID,
			err,
		)
	}
	log.Infof("[CLIENT %v] Closed socket connection", client.config.ID)
	return err
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	manager, err := NewParticipantsManager(c.config)
	c.manager = nil
	if err != nil {
		log.Fatalf(
			"[CLIENT %v] Could not connect to server. Error: %v",
			c.config.ID,
			err,
		)
	}
	c.manager = manager
	return err
}

func (c *Client) printBatchResult(batch_number int, result []Participant) {
	log.Infof("[CLIENT %v] Batch: %d", c.config.ID, batch_number)
	if len(result) == 0 {
		log.Infof("[CLIENT %v] No participant has won the lottery this batch", c.config.ID)
	} else {
		log.Infof("[CLIENT %v] Winners:", c.config.ID)
		for _, winner := range result {
			log.Infof("[CLIENT %v] First name: %s", c.config.ID, winner.first_name)
			log.Infof("[CLIENT %v] Last name: %s", c.config.ID, winner.last_name)
			log.Infof("[CLIENT %v] Document: %s", c.config.ID, winner.document)
			log.Infof("[CLIENT %v] Birthdate: %s", c.config.ID, winner.birthdate)
			log.Infof("[CLIENT %v]", c.config.ID)
		}
	}
	log.Infof("[CLIENT %v]", c.config.ID)
}

func (c *Client) processBatch(batch_number *int, total_participants_amount *int, sent_participants_amount *int, winners_amount *int) (bool, error) {
	result, is_app_error, error_message := c.manager.ReceiveWinningParticipants()
	if is_app_error {
		log.Infof("[CLIENT %v] Application logic error: %v", c.config.ID, error_message)
		return false, error_message
	} else if error_message != nil {
		logErrorMessage(c.config.ID, error_message)
		return false, error_message
	}
	*total_participants_amount += *sent_participants_amount
	*winners_amount += len(result)
	// c.printBatchResult(*batch_number, result)
	*batch_number += 1
	current_sent_participants_amount, has_file_finished, sending_err := c.manager.SendParticipants()
	if sending_err != nil {
		logErrorMessage(c.config.ID, sending_err)
		return false, sending_err
	}
	*sent_participants_amount = current_sent_participants_amount
	return !has_file_finished, nil
	// should_keep_sending_participants = !has_file_finished
}

func ask_for_winners_amount(sync_channel chan bool, client_id string, sleep_time uint32, connection_string string) {
	results_manager := NewResultManager(connection_string)
	should_keep_iterating := true
	for should_keep_iterating {
		received_amount, is_final_value, err := results_manager.getWinnersAmount()
		if err != nil {
			should_keep_iterating = false
			log.Infof("[CLIENT %v] Communication error in results manager thread: %v", client_id, err)
		}
		if is_final_value {
			should_keep_iterating = false
			log.Infof("[CLIENT %v] Total winners amount: %d", client_id, received_amount)
		} else {
			log.Infof("[CLIENT %v] Processing agencies left: %d", client_id, received_amount)
			time.Sleep(time.Second * time.Duration(sleep_time))
		}
		select {
		case <- sync_channel:
			should_keep_iterating = false
		default:
		}
	}
	sync_channel <- true
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	// Create the connection the server in every loop iteration. Send an
	// autoincremental msgID to identify every message sent
	sync_channel := make(chan bool, 1)
	signal_channel := make(chan os.Signal, 1)
	signal.Notify(signal_channel, syscall.SIGTERM)

	err := c.createClientSocket()
	if err != nil {
		log.Fatalf(
			"[CLIENT %v] Could not connect to server. Error: %v",
			c.config.ID,
			err,
		)
		return
	}
	defer closeParticipantsManager(c)
	go ask_for_winners_amount(sync_channel, c.config.ID, c.config.RequestAwait, c.config.ServerAddress)

	batch_number := 1
	total_participants_amount := 0
	winners_amount := 0
	sent_participants_amount, has_file_finished, sending_err := c.manager.SendParticipants()
	if sending_err != nil {
		logErrorMessage(c.config.ID, sending_err)
		return
	}
	should_keep_sending_participants := !has_file_finished
	for should_keep_sending_participants {
		should_keep_sending_participants, err = c.processBatch(&batch_number, &total_participants_amount, &sent_participants_amount, &winners_amount)

		if err != nil {
			return
		}

		// Process SIGTERM
		select {
		case <-signal_channel:
			log.Infof("[CLIENT %v] SIGTERM received", c.config.ID)
			closeParticipantsManager(c)
			sync_channel <- true
			<- sync_channel
			log.Infof("[CLIENT %v] Joined result getter thread", c.config.ID)
			os.Exit(143)
		default:
		}
	}
	c.processBatch(&batch_number, &total_participants_amount, &sent_participants_amount, &winners_amount)
	log.Infof("[CLIENT %v] Winners amount: %d", c.config.ID, winners_amount)
	log.Infof("[CLIENT %v] Total participants amount: %d", c.config.ID, total_participants_amount)
	log.Infof("[CLIENT %v] Finished participants evaluations, winner rate is: %f", c.config.ID, float32(winners_amount)/float32(total_participants_amount))
	closeParticipantsManager(c)
	<- sync_channel
}
