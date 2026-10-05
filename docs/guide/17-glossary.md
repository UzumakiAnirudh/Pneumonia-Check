# Chapter 17 — Glossary

[← Chapter 16](16-troubleshooting-faq.md) · [README](../../README.md)

Every technical term used in this guide, in alphabetical order.

| Term                            | Meaning                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Accuracy**                    | Share of all predictions that are correct                                                                           |
| **Activation function**         | A non-linear function applied after a weighted sum (ReLU, GELU) so networks can learn complex patterns              |
| **AdamW**                       | An optimiser that adapts each weight's step size and applies weight decay                                           |
| **API**                         | The set of URLs a server offers for programs to call                                                                |
| **AP / PA view**                | Frontal chest X-ray taken front-to-back (AP) or back-to-front (PA)                                                  |
| **Arg-max**                     | The class with the highest score                                                                                    |
| **Attention (self-attention)**  | Each token weighs every other token by similarity (queries·keys) and averages their values                          |
| **Augmentation**                | Random changes to training images (rotate, zoom, brightness) so the model generalises                               |
| **AUC (ROC-AUC)**               | Area under the ROC curve; 1 = perfect ranking, 0.5 = coin flip                                                      |
| **Backend**                     | The server-side program (here FastAPI in `backend/`)                                                                |
| **Backpropagation**             | Algorithm that computes all gradients from the loss backwards through the network                                   |
| **Batch**                       | A group of images processed together (32 here)                                                                      |
| **Batch Normalization (BN)**    | Rescales channel activations to a stable range during training                                                      |
| **Bilateral**                   | Affecting both lungs                                                                                                |
| **Calibration**                 | Whether predicted confidences match real accuracy                                                                   |
| **Channel**                     | One layer of an image or feature map (RGB has 3)                                                                    |
| **CLAHE**                       | Contrast Limited Adaptive Histogram Equalisation — local contrast enhancement                                       |
| **Class imbalance**             | Some classes have many more examples than others                                                                    |
| **Class weights**               | Making mistakes on rare classes cost more in the loss                                                               |
| **CNN**                         | Convolutional neural network                                                                                        |
| **Commit**                      | A saved snapshot in Git history                                                                                     |
| **Confusion matrix**            | Table of true vs predicted classes (TP, TN, FP, FN)                                                                 |
| **Consolidation**               | Lung tissue filled with fluid/pus, appearing white on X-ray — typical of bacterial pneumonia                        |
| **Convex hull**                 | The smallest shape without dents that encloses a set of points                                                      |
| **Convolution**                 | Sliding a small filter over an image computing weighted sums                                                        |
| **Cookie**                      | Small data the browser stores and sends back to the same site; holds the login session                              |
| **CORS**                        | Browser rules about which websites may call an API                                                                  |
| **Cross-entropy loss**          | −log(probability given to the correct class)                                                                        |
| **CSRF**                        | Attack where another site tricks your browser into sending a request with your cookies; blocked by SameSite cookies |
| **CSV**                         | A table stored as text with comma-separated values                                                                  |
| **Data leakage**                | Test information sneaking into training (e.g. the same patient in both)                                             |
| **Dense block / DenseNet**      | Layers that receive all previous layers' outputs concatenated (Chapter 6)                                           |
| **DICOM**                       | Standard medical image format, includes patient metadata                                                            |
| **Domain shift**                | New data differs from training data (hospital, machine, age)                                                        |
| **Early stopping**              | Stop training when the validation score stops improving                                                             |
| **ECE**                         | Expected Calibration Error — average gap between confidence and accuracy                                            |
| **Endpoint**                    | One URL + method of an API, e.g. `POST /api/predict`                                                                |
| **Environment variable**        | A named setting given to a program from outside (e.g. `DATABASE_URL`)                                               |
| **Epoch**                       | One full pass over the training data                                                                                |
| **External validation**         | Testing on data from a different source than training                                                               |
| **F1-score**                    | Harmonic mean of precision and recall                                                                               |
| **False negative / positive**   | Missed disease / false alarm                                                                                        |
| **FastAPI**                     | Python framework for building APIs                                                                                  |
| **Feature map**                 | The output of one filter over an image                                                                              |
| **Fine-tuning**                 | Continuing to train a pretrained network on new data                                                                |
| **Frontend**                    | The part that runs in the browser (React in `frontend/`)                                                            |
| **GAP**                         | Global average pooling — average each feature map to one number                                                     |
| **GELU**                        | A smooth activation function used in transformers                                                                   |
| **Git / GitHub**                | Version-control tool / website hosting Git repositories                                                             |
| **Gradient**                    | How much and in which direction the loss changes when a weight changes                                              |
| **Gradient descent**            | Repeatedly moving weights against the gradient to reduce the loss                                                   |
| **Grad-CAM**                    | Heatmap of the regions that increased the predicted class score (Chapter 7)                                         |
| **Hash (password hash)**        | One-way scramble of a password; PBKDF2 here                                                                         |
| **Heatmap**                     | Colour overlay showing where the model looked (blue low → red high)                                                 |
| **Hook (React)**                | A `use...` function that adds state or effects to a component                                                       |
| **HTTP / HTTPS**                | The web's request/response protocol / its encrypted version                                                         |
| **httpOnly**                    | Cookie flag: page scripts cannot read it                                                                            |
| **Hyper-parameter**             | A setting chosen by people, not learned (learning rate, batch size)                                                 |
| **ImageNet**                    | 1.2 million labelled photos used to pretrain the networks                                                           |
| **Inference**                   | Using a trained model to make predictions                                                                           |
| **Interstitial**                | Pattern of fine lines/haze between air spaces — typical of viral pneumonia                                          |
| **JSON**                        | Text format for structured data                                                                                     |
| **JSX / TSX**                   | HTML-like syntax inside JavaScript/TypeScript for React                                                             |
| **Label**                       | The correct answer for a training example                                                                           |
| **Layer Normalization**         | Normalises each token's vector (used in transformers)                                                               |
| **Learning rate**               | Size of each weight update step                                                                                     |
| **localhost**                   | "This computer" as a network address                                                                                |
| **Logits**                      | Raw scores before softmax                                                                                           |
| **Loss**                        | A number measuring how wrong the predictions are                                                                    |
| **Macro average**               | Average of a metric computed per class                                                                              |
| **Mixed precision**             | Using 16-bit floats where safe to train faster                                                                      |
| **MPS**                         | Apple's GPU backend for PyTorch on M-series Macs                                                                    |
| **Multi-head attention**        | Several attention computations in parallel                                                                          |
| **Neural network**              | A function made of layers of weighted sums and activations, learned from data                                       |
| **Normalisation (images)**      | Subtracting a mean and dividing by a standard deviation                                                             |
| **npm**                         | Package manager for JavaScript                                                                                      |
| **ONNX / ONNX Runtime**         | Portable model file format / a light engine that runs it without PyTorch                                            |
| **Optimizer**                   | Rule for updating weights from gradients                                                                            |
| **Otsu threshold**              | Automatic threshold that best separates dark and bright pixels                                                      |
| **Overfitting**                 | Memorising training data instead of learning general patterns                                                       |
| **Parameter / weight**          | A number the network learns                                                                                         |
| **Patch merging**               | Swin's downsampling: join 2×2 neighbouring tokens                                                                   |
| **Path**                        | The address of a file or folder                                                                                     |
| **PBKDF2**                      | Slow, salted password-hashing algorithm                                                                             |
| **Pip**                         | Python package installer                                                                                            |
| **Pooling**                     | Shrinking a feature map by taking max/average of small blocks                                                       |
| **Port**                        | A numbered "door" a server listens on (8000, 5173)                                                                  |
| **Precision**                   | Of predicted positives, the share that are truly positive                                                           |
| **Preprocessing**               | Preparing images before the model (grayscale, resize, CLAHE, normalise)                                             |
| **Pretrained**                  | Already trained on another dataset (ImageNet)                                                                       |
| **Pydantic**                    | Python library for validating data shapes                                                                           |
| **Quantization**                | Storing weights with fewer bits (8 instead of 32) to save memory                                                    |
| **Radiological convention**     | Patient's right appears on the image's left                                                                         |
| **React**                       | JavaScript library for building interfaces from components                                                          |
| **Receptive field**             | The part of the input image one neuron can "see"                                                                    |
| **Recall / Sensitivity**        | Of the truly sick, the share detected                                                                               |
| **ReLU**                        | max(0, x)                                                                                                           |
| **Repository (repo)**           | A project tracked by Git                                                                                            |
| **Residual connection**         | Adding a layer's input to its output (skip connection)                                                              |
| **ROC curve**                   | Sensitivity vs 1 − specificity across all thresholds                                                                |
| **Route**                       | A URL handled by the server or by React's router                                                                    |
| **Salt**                        | Random data mixed into a password before hashing                                                                    |
| **SameSite**                    | Cookie flag limiting cross-site sending (CSRF protection)                                                           |
| **Session**                     | A logged-in state identified by a random token                                                                      |
| **Shifted windows**             | Swin's trick to let attention windows exchange information                                                          |
| **Shortcut learning**           | Learning an accidental clue instead of the real signal                                                              |
| **Softmax**                     | Turns scores into probabilities that sum to 1                                                                       |
| **Specificity**                 | Of the truly healthy, the share correctly cleared                                                                   |
| **SQL / SQLite / PostgreSQL**   | Database query language / a single-file database / a server database                                                |
| **State**                       | Data in an app that changes over time                                                                               |
| **Stride**                      | How far a filter moves at each step                                                                                 |
| **Swin Transformer**            | Hierarchical vision transformer with shifted-window attention (Chapter 6)                                           |
| **Tailwind CSS**                | Styling with small utility class names                                                                              |
| **Temperature scaling**         | Dividing logits by T to calibrate confidence                                                                        |
| **Tensor**                      | A multi-dimensional array of numbers                                                                                |
| **Terminal**                    | Text window for typing commands                                                                                     |
| **Test set**                    | Data used only for the final score                                                                                  |
| **timm**                        | Library of ready-made image model architectures                                                                     |
| **Token**                       | One element in a transformer's sequence (an image patch here)                                                       |
| **Transfer learning**           | Reusing a model trained on one task for another                                                                     |
| **Transition layer**            | DenseNet's layer that shrinks channels and image size between blocks                                                |
| **TypeScript**                  | JavaScript with types                                                                                               |
| **Uvicorn**                     | The program that runs a FastAPI app on a port                                                                       |
| **Validation set**              | Data used to choose epochs and calibrate — not for the final score                                                  |
| **Virtual environment (.venv)** | A private folder of Python libraries for one project                                                                |
| **Vision Transformer (ViT)**    | Transformer applied to image patches                                                                                |
| **Vite**                        | Fast development server and build tool for the website                                                              |
| **Weight decay**                | Gently pulling weights towards zero to reduce overfitting                                                           |
| **Window attention**            | Attention computed only inside small windows (7×7 tokens)                                                           |

---

[← Back to the README](../../README.md)
