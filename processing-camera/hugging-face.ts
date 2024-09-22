import axios, { AxiosResponse } from 'axios';
import fs from 'fs';
import { API_TOKEN } from './token';

// Using a model better suited for object detection and scene understanding
const MODEL_URL: string ="https://api-inference.huggingface.co/models/dandelin/vilt-b32-finetuned-vqa"

interface DetectionResult {
  label: string;
  score: number;
  box: { xmin: number; ymin: number; xmax: number; ymax: number };
}

async function analyzeBillboard(imagePath: string): Promise<string> {
  try {
    // Read the image file as a Buffer
    const imageBuffer: Buffer = await fs.promises.readFile(imagePath);

    const response: AxiosResponse<DetectionResult[]> = await axios.post(
      MODEL_URL,
      imageBuffer,
      {
        headers: {
          'Authorization': `Bearer ${API_TOKEN}`,
          'Content-Type': 'application/octet-stream'
        },
      }
    );

    console.log('Response:', response.data);
    return "Analysis successful";
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      console.error('Error:', error.response.data);
      throw new Error(`API request failed: ${error.response.status}`);
    } else {
      console.error('Error:', error);
      throw new Error('An unexpected error occurred');
    }
  }
}


async function isBillboardRunning(imagePath:string) {
  var bitmap = fs.readFileSync(imagePath);
  let image = new Buffer(bitmap).toString('base64');

  try {
    const response = await axios.post(MODEL_URL, {
      inputs:{
        image: image,
        question: "Is the billboard running",
        topK:1
      }
    }, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        // @ts-ignore
        // ...form.getHeaders(),
      },
    });
    if(response.data){
      return response.data[0].answer == 'yes';
    }else{
      throw new Error('No response from model');
    }
    

  } catch (error:any) {
    console.error('Error in request:', error.response ? error.response.data : error.message);
    throw new Error('An unexpected error occurred');
  }
}

// Use the specific image path
const imagePath: string = './processing-camera/WhatsApp_Image_2024-09-22_at_13.16.35.jpg';

function postStatus(status: boolean) {
  console.log(status);
}

function init(){

  setInterval(() => {
    isBillboardRunning(imagePath).then((result) => {
      postStatus(result);
    }).catch((error) => {
      console.error(error);
    });
  }, 60000);
}

init();